from __future__ import annotations

from random import choices
from string import digits
from typing import cast

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.redis import get_redis_client
from app.core.security import create_access_token, hash_password, verify_password
from app.models.commission import UserCommission
from app.models.enums import GlobalRole, UserStatus
from app.models.user import InviteRecord, User
from app.services.asset_service import init_user_assets
from app.services.sms_service import SmsService
from app.utils.helpers import generate_code, now


class AuthService:
    LOGIN_CODE_LENGTH = 6
    LOGIN_CODE_TTL_SECONDS = 300
    LOGIN_CODE_RESEND_INTERVAL_SECONDS = 60
    LOGIN_CODE_KEY_PREFIX = 'auth:login_code'
    LOGIN_CODE_COOLDOWN_KEY_PREFIX = 'auth:login_code:cooldown'

    @staticmethod
    def _issue_token(user: User) -> str:
        return create_access_token(str(user.id), {'role': user.global_role.value})

    @staticmethod
    def issue_token(user: User) -> str:
        return AuthService._issue_token(user)

    @staticmethod
    def finalize_login(db: Session, user: User) -> tuple[str, User]:
        return AuthService._finalize_login(db, user)

    @staticmethod
    def _finalize_login(db: Session, user: User) -> tuple[str, User]:
        if user.status != UserStatus.ENABLED:
            raise UnauthorizedError('Account disabled')

        user.last_login_at = now()
        db.commit()
        db.refresh(user)
        return AuthService._issue_token(user), user

    @staticmethod
    def _create_user(
        db: Session,
        phone: str,
        password: str,
        nickname: str,
        invite_code: str | None = None,
    ) -> User:
        parent = db.query(User).filter(User.invite_code == invite_code).first() if invite_code else None
        user = User(
            phone=phone,
            password_hash=hash_password(password),
            nickname=nickname,
            global_role=GlobalRole.USER,
            status=UserStatus.ENABLED,
            invite_code=generate_code(length=8),
            parent_id=parent.id if parent else None,
            grandparent_id=parent.parent_id if parent else None,
        )
        db.add(user)
        db.flush()

        if parent:
            db.add(
                InviteRecord(
                    inviter_user_id=parent.id,
                    invitee_user_id=user.id,
                    level=1,
                    invite_code=invite_code or '',
                    bound_at=now(),
                )
            )
            if parent.parent_id:
                db.add(
                    InviteRecord(
                        inviter_user_id=parent.parent_id,
                        invitee_user_id=user.id,
                        level=2,
                        invite_code=invite_code or '',
                        bound_at=now(),
                    )
                )

        db.add(UserCommission(user_id=user.id, updated_at=now()))
        init_user_assets(db, user.id)
        return user

    @staticmethod
    def create_passwordless_user(
        db: Session,
        phone: str,
        nickname: str,
        invite_code: str | None = None,
    ) -> User:
        return AuthService._create_user(db, phone, generate_code(length=12), nickname, invite_code)

    @staticmethod
    def _login_code_key(phone: str) -> str:
        return f'{AuthService.LOGIN_CODE_KEY_PREFIX}:{phone}'

    @staticmethod
    def _login_code_cooldown_key(phone: str) -> str:
        return f'{AuthService.LOGIN_CODE_COOLDOWN_KEY_PREFIX}:{phone}'

    @staticmethod
    def _generate_login_code() -> str:
        return ''.join(choices(digits, k=AuthService.LOGIN_CODE_LENGTH))

    @staticmethod
    def register(db: Session, phone: str, password: str, nickname: str, invite_code: str | None = None) -> tuple[str, User]:
        existing = db.query(User).filter(User.phone == phone).first()
        if existing:
            raise ConflictError('Phone already registered')

        user = AuthService._create_user(db, phone, password, nickname, invite_code)
        db.commit()
        db.refresh(user)
        return AuthService._issue_token(user), user

    @staticmethod
    def login(db: Session, phone: str, password: str, admin_only: bool = False) -> tuple[str, User]:
        user = db.query(User).filter(User.phone == phone).first()
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError('Phone or password invalid')
        if admin_only and user.global_role not in {GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN}:
            raise UnauthorizedError('Admin account required')
        if admin_only and user.global_role == GlobalRole.TEAM_ADMIN:
            role = user.admin_role
            if user.admin_role_id and (not role or role.status != 'ENABLED'):
                raise UnauthorizedError('Admin role disabled')
        return AuthService._finalize_login(db, user)

    @staticmethod
    def send_login_code(phone: str) -> dict:
        """
        发送登录验证码

        1. 检查发送频率限制（使用Redis）
        2. 生成6位验证码
        3. 通过阿里云短信服务发送
        4. 开发环境下返回验证码方便测试
        """
        redis = get_redis_client()

        # 1. 检查发送频率
        cooldown_key = AuthService._login_code_cooldown_key(phone)
        if redis:
            ttl = cast(int, redis.ttl(cooldown_key))
            if ttl and ttl > 0:
                raise ConflictError(f'Code already sent, retry in {ttl}s')

        # 2. 生成验证码（用于Redis校验）
        code = AuthService._generate_login_code()

        # 3. 存储验证码到Redis（用于后续验证）
        if redis:
            redis.setex(AuthService._login_code_key(phone), AuthService.LOGIN_CODE_TTL_SECONDS, code)
            redis.setex(cooldown_key, AuthService.LOGIN_CODE_RESEND_INTERVAL_SECONDS, '1')

        # 4. 发送短信（仅在启用短信服务时）
        sms_sent = False
        if settings.sms_enabled and settings.sms_aliyun_access_key_id:
            try:
                SmsService.send_login_code(phone, code)
                sms_sent = True
            except Exception as e:
                if redis:
                    redis.delete(AuthService._login_code_key(phone))
                    redis.delete(cooldown_key)
                import logging
                logging.warning(f'SMS send failed for {phone}: {str(e)}')
                if settings.app_env.lower() == 'production':
                    raise ConflictError(f'短信发送失败: {str(e)}') from e
        else:
            # 短信服务未配置时，仅记录日志
            import logging
            logging.warning(f'SMS not configured, code for {phone}: {code}')
            if settings.app_env.lower() == 'production':
                raise ConflictError('短信服务未配置')

        response: dict[str, int | str] = {
            'expires_in': AuthService.LOGIN_CODE_TTL_SECONDS,
            'retry_in': AuthService.LOGIN_CODE_RESEND_INTERVAL_SECONDS,
        }
        # 开发环境 或 短信未成功发送时，返回验证码方便测试
        if settings.app_env.lower() == 'development' or not sms_sent:
            response['debug_code'] = code
        return response

    @staticmethod
    def login_by_code(db: Session, phone: str, code: str, invite_code: str | None = None) -> tuple[str, User]:
        redis = get_redis_client()
        cached_code = redis.get(AuthService._login_code_key(phone))
        if not cached_code:
            raise UnauthorizedError('Verification code expired')
        if str(cached_code) != str(code):
            raise UnauthorizedError('Verification code invalid')

        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            user = AuthService._create_user(
                db,
                phone=phone,
                password=generate_code(length=12),
                nickname=f'用户{phone[-4:]}',
                invite_code=invite_code,
            )
        elif invite_code and not user.parent_id:
            from app.services.user_service import UserService

            UserService.bind_inviter(db, user, invite_code)

        redis.delete(AuthService._login_code_key(phone))

        return AuthService._finalize_login(db, user)

    @staticmethod
    def reset_password(db: Session, phone: str, new_password: str) -> None:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            raise UnauthorizedError('User not found')
        user.password_hash = hash_password(new_password)
        db.commit()
