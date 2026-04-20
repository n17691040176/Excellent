from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.asset import UserAssetAccount, UserAssetLedger, UserPowerBank
from app.models.enums import GlobalRole, UserStatus
from app.models.order import Order
from app.models.user import InviteRecord, User, UserLegacyProfile
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import AssetService


class UserService:
    @staticmethod
    def is_legacy_user(db: Session, user: User | int | None) -> bool:
        user_id = user.id if isinstance(user, User) else user
        if not user_id:
            return False
        return db.get(UserLegacyProfile, user_id) is not None

    @staticmethod
    def serialize_app_user(db: Session, user: User) -> dict:
        return {
            'id': user.id,
            'user_id': user.id,
            'phone': user.phone,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'global_role': user.global_role.value,
            'business_identity': user.business_identity.value,
            'status': user.status.value,
            'invite_code': user.invite_code,
            'parent_id': user.parent_id,
            'grandparent_id': user.grandparent_id,
            'team_id': user.team_id,
            'real_name': user.real_name,
            'last_login_at': user.last_login_at,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'is_legacy_user': UserService.is_legacy_user(db, user),
            'is_legacy_imported': UserService.is_legacy_user(db, user),
        }

    @staticmethod
    def serialize_admin_user(user: User, legacy_profile: UserLegacyProfile | None = None) -> dict:
        return {
            'id': user.id,
            'phone': user.phone,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'global_role': user.global_role.value,
            'business_identity': user.business_identity.value,
            'status': user.status.value,
            'invite_code': user.invite_code,
            'parent_id': user.parent_id,
            'grandparent_id': user.grandparent_id,
            'team_id': user.team_id,
            'real_name': user.real_name,
            'last_login_at': user.last_login_at,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'is_legacy_imported': legacy_profile is not None,
            'legacy_user_id': legacy_profile.legacy_user_id if legacy_profile else None,
        }

    @staticmethod
    def update_profile(db: Session, current_user: User, payload: dict) -> User:
        for field, value in payload.items():
            if value is not None and hasattr(current_user, field):
                setattr(current_user, field, value)
        db.commit()
        db.refresh(current_user)
        return current_user

    @staticmethod
    def list_users(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        role: GlobalRole | None = None,
        source: str | None = None,
    ) -> list[dict]:
        query = db.query(User, UserLegacyProfile).outerjoin(UserLegacyProfile, UserLegacyProfile.user_id == User.id)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(User.team_id == AdminScopeService.require_team_id(current_user))
        if role:
            query = query.filter(User.global_role == role)
        if source == 'legacy':
            query = query.filter(UserLegacyProfile.user_id.isnot(None))
        elif source == 'native':
            query = query.filter(UserLegacyProfile.user_id.is_(None))
        if keyword:
            like_value = f'%{keyword.strip()}%'
            query = query.filter(or_(
                User.phone.ilike(like_value),
                User.nickname.ilike(like_value),
                User.invite_code.ilike(like_value),
                UserLegacyProfile.phonenumber.ilike(like_value),
                UserLegacyProfile.nick_name.ilike(like_value),
                UserLegacyProfile.user_name.ilike(like_value),
                UserLegacyProfile.invite_code.ilike(like_value),
                cast(UserLegacyProfile.legacy_user_id, String).ilike(like_value),
            ))
        rows = query.distinct(User.id).order_by(User.id.desc()).all()
        return [UserService.serialize_admin_user(user, legacy_profile) for user, legacy_profile in rows]

    @staticmethod
    def get_user(db: Session, user_id: int, current_user: User | None = None) -> User:
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError('User not found')
        if current_user:
            AdminScopeService.ensure_user_visible(current_user, user)
        return user

    @staticmethod
    def get_user_legacy_profile(db: Session, user_id: int, current_user: User | None = None) -> dict:
        user = UserService.get_user(db, user_id, current_user)
        legacy_profile = db.get(UserLegacyProfile, user.id)
        if not legacy_profile:
            raise NotFoundError('Legacy profile not found')

        legacy_data = {
            column.name: getattr(legacy_profile, column.name)
            for column in UserLegacyProfile.__table__.columns
        }
        return {
            'user': UserService.serialize_admin_user(user, legacy_profile),
            'legacy_profile': legacy_data,
        }

    @staticmethod
    def get_user_for_admin(db: Session, user_id: int, current_user: User | None = None) -> dict:
        user = UserService.get_user(db, user_id, current_user)
        legacy_profile = db.get(UserLegacyProfile, user.id)
        if AssetService.ensure_user_asset_accounts(db, user.id):
            db.commit()
        AssetService.settle_power_bank_income(db, user.id)
        asset_rows = db.query(UserAssetAccount).filter(UserAssetAccount.user_id == user.id).all()
        power_banks = db.query(UserPowerBank).filter(UserPowerBank.user_id == user.id).order_by(UserPowerBank.id.desc()).all()
        asset_summary = {
            account.asset_type.value: {
                'total_amount': float(account.total_amount),
                'available_amount': float(account.available_amount),
                'frozen_amount': float(account.frozen_amount),
                'consumed_amount': float(account.consumed_amount),
                'withdrawn_amount': float(account.withdrawn_amount),
            }
            for account in asset_rows
        }
        power_bank_available = float(AssetService.active_power_bank_count(db, user.id))
        power_bank_total = float(asset_summary.get('POWER_BANK', {}).get('total_amount', 0))
        asset_summary['POWER_BANK'] = {
            'total_amount': max(power_bank_total, power_bank_available),
            'available_amount': power_bank_available,
            'frozen_amount': 0.0,
            'consumed_amount': float(asset_summary.get('POWER_BANK', {}).get('consumed_amount', 0)),
            'withdrawn_amount': 0.0,
        }
        asset_ledger_rows = db.query(UserAssetLedger).filter(
            UserAssetLedger.user_id == user.id,
        ).order_by(UserAssetLedger.id.desc()).limit(10).all()
        recent_orders = db.query(Order).filter(
            Order.user_id == user.id,
        ).order_by(Order.id.desc()).limit(10).all()
        invite_summary = {
            'level1_count': int(db.query(func.count(User.id)).filter(User.parent_id == user.id).scalar() or 0),
            'level2_count': int(db.query(func.count(User.id)).filter(User.grandparent_id == user.id).scalar() or 0),
        }
        return {
            **UserService.serialize_admin_user(user, legacy_profile),
            'asset_summary': asset_summary,
            'power_banks': [
                {
                    'id': item.id,
                    'device_code': item.device_code,
                    'device_name': item.device_name,
                    'status': item.status.value,
                    'bound_at': item.bound_at,
                    'last_income_date': item.last_income_date,
                    'total_income_amount': float(item.total_income_amount),
                    'total_referral_income_amount': float(item.total_referral_income_amount),
                    'remark': item.remark,
                    'created_at': item.created_at,
                    'updated_at': item.updated_at,
                }
                for item in power_banks
            ],
            'recent_asset_ledgers': [
                {
                    'id': item.id,
                    'asset_type': item.asset_type.value,
                    'direction': item.direction.value,
                    'change_amount': float(item.change_amount),
                    'before_amount': float(item.before_amount),
                    'after_amount': float(item.after_amount),
                    'business_type': item.business_type,
                    'source_id': item.source_id,
                    'source_no': item.source_no,
                    'remark': item.remark,
                    'created_at': item.created_at,
                }
                for item in asset_ledger_rows
            ],
            'recent_orders': [
                {
                    'id': item.id,
                    'order_no': item.order_no,
                    'order_type': item.order_type.value,
                    'zone_type': item.zone_type.value if item.zone_type else None,
                    'total_amount': float(item.total_amount),
                    'payable_amount': float(item.payable_amount),
                    'paid_amount': float(item.paid_amount),
                    'pay_status': item.pay_status.value,
                    'order_status': item.order_status.value,
                    'created_at': item.created_at,
                    'paid_at': item.paid_at,
                }
                for item in recent_orders
            ],
            'invite_summary': {
                **invite_summary,
                'total_count': invite_summary['level1_count'] + invite_summary['level2_count'],
            },
        }

    @staticmethod
    def update_user_status(db: Session, user_id: int, status: UserStatus) -> User:
        user = UserService.get_user(db, user_id)
        user.status = status
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_invite_tree(db: Session, user_id: int, current_user: User | None = None) -> dict:
        user = UserService.get_user(db, user_id, current_user)
        level1 = db.query(User).filter(User.parent_id == user.id).all()
        level2 = db.query(User).filter(User.grandparent_id == user.id).all()
        if current_user and not AdminScopeService.is_super_admin(current_user):
            team_id = AdminScopeService.require_team_id(current_user)
            level1 = [item for item in level1 if item.team_id == team_id]
            level2 = [item for item in level2 if item.team_id == team_id]
        return {
            'user_id': user.id,
            'phone': user.phone,
            'level1': [{'id': item.id, 'phone': item.phone, 'nickname': item.nickname} for item in level1],
            'level2': [{'id': item.id, 'phone': item.phone, 'nickname': item.nickname} for item in level2],
        }
