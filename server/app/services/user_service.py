from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.api.v1.mobile_serializers import (
    serialize_address,
    serialize_cart_item,
    serialize_favorite_product,
    serialize_footprint,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.models.address import UserAddress
from app.models.asset import UserAssetAccount, UserAssetLedger, UserPowerBank
from app.models.commerce import ShoppingCartItem, UserFavoriteProduct, UserProductFootprint
from app.models.commission import UserCommission
from app.models.enums import GlobalRole, MemberLevel, UserStatus
from app.models.order import Order
from app.models.user import InviteRecord, User, UserLegacyProfile
from app.services.admin_permission_service import AdminPermissionService
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import AssetService
from app.utils.helpers import iso_datetime, now


class UserService:
    @staticmethod
    def bind_inviter(db: Session, current_user: User, invite_code: str) -> dict:
        clean_code = invite_code.strip()
        inviter = db.query(User).filter(func.upper(User.invite_code) == clean_code.upper()).first()
        if not inviter:
            raise NotFoundError('邀请码无效')
        if inviter.id == current_user.id:
            raise ConflictError('不能绑定自己为上级')

        # Lock the row where supported so two concurrent scans cannot bind different inviters.
        user = db.query(User).filter(User.id == current_user.id).with_for_update().one()
        if user.parent_id:
            if user.parent_id == inviter.id:
                return UserService._serialize_invite_binding(user, inviter, already_bound=True)
            raise ConflictError('当前账号已绑定上级，不能重复绑定')

        ancestor = inviter
        visited: set[int] = set()
        while ancestor:
            if ancestor.id == user.id:
                raise ConflictError('不能绑定自己的下级为上级')
            if ancestor.id in visited or not ancestor.parent_id:
                break
            visited.add(ancestor.id)
            ancestor = db.get(User, ancestor.parent_id)

        user.parent_id = inviter.id
        user.grandparent_id = inviter.parent_id
        bound_at = now()
        UserService._add_invite_record(
            db,
            inviter_user_id=inviter.id,
            invitee_user_id=user.id,
            level=1,
            invite_code=inviter.invite_code,
            bound_at=bound_at,
        )
        if inviter.parent_id:
            UserService._add_invite_record(
                db,
                inviter_user_id=inviter.parent_id,
                invitee_user_id=user.id,
                level=2,
                invite_code=inviter.invite_code,
                bound_at=bound_at,
            )

        # Existing direct invitees become level-two invitees of the newly bound inviter.
        direct_invitees = db.query(User).filter(User.parent_id == user.id).all()
        for invitee in direct_invitees:
            invitee.grandparent_id = inviter.id
            UserService._add_invite_record(
                db,
                inviter_user_id=inviter.id,
                invitee_user_id=invitee.id,
                level=2,
                invite_code=inviter.invite_code,
                bound_at=bound_at,
            )

        db.commit()
        db.refresh(user)
        return UserService._serialize_invite_binding(user, inviter, already_bound=False)

    @staticmethod
    def _add_invite_record(
        db: Session,
        *,
        inviter_user_id: int,
        invitee_user_id: int,
        level: int,
        invite_code: str,
        bound_at,
    ) -> None:
        exists = db.query(InviteRecord.id).filter(
            InviteRecord.inviter_user_id == inviter_user_id,
            InviteRecord.invitee_user_id == invitee_user_id,
            InviteRecord.level == level,
        ).first()
        if not exists:
            db.add(
                InviteRecord(
                    inviter_user_id=inviter_user_id,
                    invitee_user_id=invitee_user_id,
                    level=level,
                    invite_code=invite_code,
                    bound_at=bound_at,
                )
            )

    @staticmethod
    def _serialize_invite_binding(user: User, inviter: User, *, already_bound: bool) -> dict:
        return {
            'user_id': user.id,
            'parent_id': user.parent_id,
            'grandparent_id': user.grandparent_id,
            'already_bound': already_bound,
            'inviter': {
                'id': inviter.id,
                'nickname': inviter.nickname,
                'invite_code': inviter.invite_code,
            },
        }

    @staticmethod
    def _user_list_query(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        role: GlobalRole | None = None,
        member_level: MemberLevel | None = None,
        source: str | None = None,
    ):
        query = db.query(User, UserLegacyProfile).outerjoin(UserLegacyProfile, UserLegacyProfile.user_id == User.id)
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(User.team_id == AdminScopeService.require_team_id(current_user))
        if role:
            query = query.filter(User.global_role == role)
        if member_level:
            query = query.filter(User.member_level == member_level)
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
        return query

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
            'admin_role': {
                'id': user.admin_role.id,
                'code': user.admin_role.code,
                'name': user.admin_role.name,
                'data_scope': user.admin_role.data_scope,
                'status': user.admin_role.status,
            } if user.admin_role else None,
            'member_level': user.member_level.value,
            'member_level_name': user.member_level.label,
            'status': user.status.value,
            'invite_code': user.invite_code,
            'parent_id': user.parent_id,
            'grandparent_id': user.grandparent_id,
            'team_id': user.team_id,
            'real_name': user.real_name,
            'last_login_at': iso_datetime(user.last_login_at),
            'created_at': iso_datetime(user.created_at),
            'updated_at': iso_datetime(user.updated_at),
            'is_legacy_user': UserService.is_legacy_user(db, user),
            'is_legacy_imported': UserService.is_legacy_user(db, user),
            'permissions': AdminPermissionService.effective_permissions(db, user),
        }

    @staticmethod
    def serialize_admin_user(user: User, legacy_profile: UserLegacyProfile | None = None) -> dict:
        return {
            'id': user.id,
            'phone': user.phone,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'global_role': user.global_role.value,
            'admin_role': {
                'id': user.admin_role.id,
                'code': user.admin_role.code,
                'name': user.admin_role.name,
                'data_scope': user.admin_role.data_scope,
                'status': user.admin_role.status,
            } if user.admin_role else None,
            'member_level': user.member_level.value,
            'member_level_name': user.member_level.label,
            'status': user.status.value,
            'invite_code': user.invite_code,
            'parent_id': user.parent_id,
            'grandparent_id': user.grandparent_id,
            'team_id': user.team_id,
            'real_name': user.real_name,
            'last_login_at': iso_datetime(user.last_login_at),
            'created_at': iso_datetime(user.created_at),
            'updated_at': iso_datetime(user.updated_at),
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
        member_level: MemberLevel | None = None,
        source: str | None = None,
    ) -> list[dict]:
        query = UserService._user_list_query(
            db, current_user, keyword=keyword, role=role, member_level=member_level, source=source
        )
        rows = query.distinct(User.id).order_by(User.id.desc()).all()
        return [UserService.serialize_admin_user(user, legacy_profile) for user, legacy_profile in rows]

    @staticmethod
    def list_users_page(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        role: GlobalRole | None = None,
        member_level: MemberLevel | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 100))
        query = UserService._user_list_query(
            db, current_user, keyword=keyword, role=role, member_level=member_level, source=source
        )
        total = int(
            query.order_by(None).with_entities(func.count(func.distinct(User.id))).scalar() or 0
        )
        rows = (
            query.distinct(User.id)
            .order_by(User.id.desc())
            .offset((safe_page - 1) * safe_page_size)
            .limit(safe_page_size)
            .all()
        )
        return {
            'items': [UserService.serialize_admin_user(user, legacy_profile) for user, legacy_profile in rows],
            'total': total,
            'page': safe_page,
            'page_size': safe_page_size,
        }

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
        addresses = db.query(UserAddress).filter(UserAddress.user_id == user.id).order_by(UserAddress.id.desc()).all()
        favorite_total = int(db.query(func.count(UserFavoriteProduct.id)).filter(UserFavoriteProduct.user_id == user.id).scalar() or 0)
        footprint_total = int(db.query(func.count(UserProductFootprint.id)).filter(UserProductFootprint.user_id == user.id).scalar() or 0)
        cart_total = int(db.query(func.count(ShoppingCartItem.id)).filter(ShoppingCartItem.user_id == user.id).scalar() or 0)
        cart_selected_total = int(
            db.query(func.count(ShoppingCartItem.id)).filter(
                ShoppingCartItem.user_id == user.id,
                ShoppingCartItem.selected.is_(True),
            ).scalar() or 0
        )
        favorites = db.query(UserFavoriteProduct).filter(UserFavoriteProduct.user_id == user.id).order_by(UserFavoriteProduct.id.desc()).limit(20).all()
        footprints = db.query(UserProductFootprint).filter(UserProductFootprint.user_id == user.id).order_by(
            UserProductFootprint.last_viewed_at.desc(),
            UserProductFootprint.id.desc(),
        ).limit(20).all()
        cart_items = db.query(ShoppingCartItem).filter(ShoppingCartItem.user_id == user.id).order_by(
            ShoppingCartItem.updated_at.desc(),
            ShoppingCartItem.id.desc(),
        ).limit(20).all()
        visible_asset_types = {'BALANCE', 'POINTS'}
        asset_summary = {
            account.asset_type.value: {
                'total_amount': float(account.total_amount),
                'available_amount': float(account.available_amount),
                'frozen_amount': float(account.frozen_amount),
                'consumed_amount': float(account.consumed_amount),
                'withdrawn_amount': float(account.withdrawn_amount),
            }
            for account in asset_rows
            if account.asset_type.value in visible_asset_types
        }
        commission = db.query(UserCommission).filter(UserCommission.user_id == user.id).first()
        asset_summary['COMMISSION'] = {
            'total_amount': float(commission.total_amount) if commission else 0.0,
            'available_amount': float(commission.available_amount) if commission else 0.0,
            'frozen_amount': float(commission.frozen_amount) if commission else 0.0,
            'consumed_amount': 0.0,
            'withdrawn_amount': float(commission.withdrawn_amount) if commission else 0.0,
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
                    'bound_at': iso_datetime(item.bound_at),
                    'last_income_date': item.last_income_date,
                    'total_income_amount': float(item.total_income_amount),
                    'total_referral_income_amount': float(item.total_referral_income_amount),
                    'remark': item.remark,
                    'created_at': iso_datetime(item.created_at),
                    'updated_at': iso_datetime(item.updated_at),
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
                    'created_at': iso_datetime(item.created_at),
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
                    'created_at': iso_datetime(item.created_at),
                    'paid_at': iso_datetime(item.paid_at),
                }
                for item in recent_orders
            ],
            'invite_summary': {
                **invite_summary,
                'total_count': invite_summary['level1_count'] + invite_summary['level2_count'],
            },
            'commerce_summary': {
                'address_count': len(addresses),
                'default_address_count': len([item for item in addresses if item.is_default]),
                'favorite_count': favorite_total,
                'footprint_count': footprint_total,
                'cart_item_count': cart_total,
                'cart_selected_count': cart_selected_total,
            },
            'addresses': [serialize_address(item) for item in addresses],
            'favorites': [serialize_favorite_product(db, item) for item in favorites],
            'footprints': [serialize_footprint(db, item) for item in footprints],
            'cart_items': [serialize_cart_item(db, item) for item in cart_items],
        }

    @staticmethod
    def update_user_status(db: Session, user_id: int, status: UserStatus) -> User:
        user = UserService.get_user(db, user_id)
        user.status = status
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_member_level(
        db: Session,
        user_id: int,
        member_level: MemberLevel,
        current_user: User | None = None,
    ) -> dict:
        user = UserService.get_user(db, user_id, current_user)
        user.member_level = member_level
        db.commit()
        db.refresh(user)
        legacy_profile = db.get(UserLegacyProfile, user.id)
        return UserService.serialize_admin_user(user, legacy_profile)

    @staticmethod
    def get_invite_tree(db: Session, user_id: int, current_user: User | None = None) -> dict:
        user = UserService.get_user(db, user_id, current_user)
        level1 = db.query(User).filter(User.parent_id == user.id).all()
        level2 = db.query(User).filter(User.grandparent_id == user.id).all()
        if current_user and not AdminScopeService.has_global_scope(current_user):
            team_id = AdminScopeService.require_team_id(current_user)
            level1 = [item for item in level1 if item.team_id == team_id]
            level2 = [item for item in level2 if item.team_id == team_id]
        return {
            'user_id': user.id,
            'phone': user.phone,
            'level1': [{'id': item.id, 'phone': item.phone, 'nickname': item.nickname} for item in level1],
            'level2': [{'id': item.id, 'phone': item.phone, 'nickname': item.nickname} for item in level2],
        }
