from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.asset import DailySigninRecord, UserAssetAccount, UserAssetLedger
from app.models.enums import AssetDirection, AssetType
from app.models.user import User
from app.utils.helpers import now, quantize_amount, today


DEFAULT_ASSET_TYPES = [AssetType.BALANCE, AssetType.POINTS, AssetType.VOUCHER, AssetType.AI_COUPON]


def init_user_assets(db: Session, user_id: int) -> None:
    current_time = now()
    for asset_type in DEFAULT_ASSET_TYPES:
        db.add(
            UserAssetAccount(
                user_id=user_id,
                asset_type=asset_type,
                total_amount=0,
                available_amount=0,
                frozen_amount=0,
                consumed_amount=0,
                withdrawn_amount=0,
                updated_at=current_time,
            )
        )


class AssetService:
    @staticmethod
    def get_account(db: Session, user_id: int, asset_type: AssetType) -> UserAssetAccount:
        account = db.query(UserAssetAccount).filter(
            UserAssetAccount.user_id == user_id,
            UserAssetAccount.asset_type == asset_type,
        ).first()
        if not account:
            raise NotFoundError('Asset account not found')
        return account

    @staticmethod
    def add_amount(
        db: Session,
        user_id: int,
        asset_type: AssetType,
        amount: Decimal | float,
        business_type: str,
        source_id: int | None = None,
        source_no: str | None = None,
        remark: str | None = None,
    ) -> UserAssetAccount:
        account = AssetService.get_account(db, user_id, asset_type)
        change = quantize_amount(amount)
        before = quantize_amount(account.available_amount)
        after = before + change
        account.total_amount = quantize_amount(account.total_amount) + change
        account.available_amount = after
        account.updated_at = now()
        db.add(
            UserAssetLedger(
                user_id=user_id,
                asset_type=asset_type,
                direction=AssetDirection.INCOME,
                change_amount=change,
                before_amount=before,
                after_amount=after,
                business_type=business_type,
                source_id=source_id,
                source_no=source_no,
                remark=remark,
                created_at=now(),
            )
        )
        return account

    @staticmethod
    def consume_amount(
        db: Session,
        user_id: int,
        asset_type: AssetType,
        amount: Decimal | float,
        business_type: str,
        source_id: int | None = None,
        source_no: str | None = None,
        remark: str | None = None,
    ) -> UserAssetAccount:
        account = AssetService.get_account(db, user_id, asset_type)
        change = quantize_amount(amount)
        before = quantize_amount(account.available_amount)
        if before < change:
            raise ConflictError(f'{asset_type.value} insufficient')
        after = before - change
        account.available_amount = after
        account.consumed_amount = quantize_amount(account.consumed_amount) + change
        account.updated_at = now()
        db.add(
            UserAssetLedger(
                user_id=user_id,
                asset_type=asset_type,
                direction=AssetDirection.EXPENSE,
                change_amount=change,
                before_amount=before,
                after_amount=after,
                business_type=business_type,
                source_id=source_id,
                source_no=source_no,
                remark=remark,
                created_at=now(),
            )
        )
        return account

    @staticmethod
    def summary(db: Session, user_id: int) -> dict:
        accounts = db.query(UserAssetAccount).filter(UserAssetAccount.user_id == user_id).all()
        return {account.asset_type.value: float(account.available_amount) for account in accounts}

    @staticmethod
    def sign_in(db: Session, user_id: int) -> dict:
        existed = db.query(DailySigninRecord).filter(
            DailySigninRecord.user_id == user_id,
            DailySigninRecord.signin_date == today(),
        ).first()
        if existed:
            raise ConflictError('Already signed in today')
        db.add(DailySigninRecord(user_id=user_id, signin_date=today(), voucher_amount=100, created_at=now()))
        AssetService.add_amount(db, user_id, AssetType.VOUCHER, 100, 'DAILY_SIGNIN')
        db.commit()
        account = AssetService.get_account(db, user_id, AssetType.VOUCHER)
        return {'voucher_reward': 100, 'voucher_balance': float(account.available_amount)}

    @staticmethod
    def transfer_points(db: Session, user: User, to_user_id: int, amount: float, remark: str | None = None) -> None:
        target = db.get(User, to_user_id)
        if not target:
            raise NotFoundError('Target user not found')
        if to_user_id not in {user.parent_id, user.grandparent_id} and user.id not in {target.parent_id, target.grandparent_id}:
            raise ConflictError('Only transfer to parent or child relations')
        AssetService.consume_amount(db, user.id, AssetType.POINTS, amount, 'POINTS_TRANSFER_OUT', remark=remark)
        AssetService.add_amount(db, target.id, AssetType.POINTS, amount, 'POINTS_TRANSFER_IN', remark=remark)
        db.commit()
