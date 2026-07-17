from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.asset import (
    DailySigninRecord,
    UserAssetAccount,
    UserAssetLedger,
    UserPowerBank,
    UserPowerBankIncomeRecord,
)
from app.models.enums import AssetDirection, AssetType, PowerBankStatus
from app.models.user import User
from app.services.earning_rule_service import PB_OWNER_DAILY_RULE, PB_REFERRAL_DAILY_RULE, EarningRuleService
from app.utils.helpers import now, quantize_amount, today

DEFAULT_ASSET_TYPES = [AssetType.BALANCE, AssetType.POINTS, AssetType.VOUCHER, AssetType.AI_COUPON, AssetType.POWER_BANK]
VISIBLE_ASSET_TOTAL_TYPES = {AssetType.BALANCE, AssetType.POINTS, AssetType.VOUCHER}
POWER_BANK_OWNER_DAILY_INCOME = Decimal('0.75')
POWER_BANK_REFERRAL_DAILY_INCOME = Decimal('0.25')


def init_user_assets(db: Session, user_id: int) -> None:
    AssetService.ensure_user_asset_accounts(db, user_id)


class AssetService:
    _power_bank_asset_account_supported: bool | None = None

    @staticmethod
    def _asset_type_supported_by_table(db: Session, table_name: str, asset_type: AssetType) -> bool:
        row = db.execute(text(f"SHOW COLUMNS FROM {table_name} LIKE 'asset_type'")).mappings().first()
        if not row:
            return True
        column_type = str(row.get('Type') or '').lower()
        if column_type.startswith(('varchar', 'char', 'text')):
            return True
        if column_type.startswith('enum('):
            return f"'{asset_type.value.lower()}'" in column_type
        return True

    @staticmethod
    def supports_power_bank_asset_account(db: Session) -> bool:
        if AssetService._power_bank_asset_account_supported is None:
            AssetService._power_bank_asset_account_supported = (
                AssetService._asset_type_supported_by_table(db, 'user_asset_accounts', AssetType.POWER_BANK)
                and AssetService._asset_type_supported_by_table(db, 'user_asset_ledgers', AssetType.POWER_BANK)
            )
        return bool(AssetService._power_bank_asset_account_supported)

    @staticmethod
    def _supported_asset_types(db: Session, asset_types: list[AssetType]) -> list[AssetType]:
        if AssetService.supports_power_bank_asset_account(db):
            return asset_types
        return [asset_type for asset_type in asset_types if asset_type != AssetType.POWER_BANK]

    @staticmethod
    def sync_power_bank_account_snapshot(
        db: Session,
        user_id: int,
        account: UserAssetAccount | None = None,
        *,
        commit: bool = True,
    ) -> UserAssetAccount:
        target_account = account or db.query(UserAssetAccount).filter(
            UserAssetAccount.user_id == user_id,
            UserAssetAccount.asset_type == AssetType.POWER_BANK,
        ).first()
        if not target_account:
            raise NotFoundError('Asset account not found')

        active_count = quantize_amount(AssetService.active_power_bank_count(db, user_id))
        total_bound_count = quantize_amount(
            db.query(UserPowerBank).filter(UserPowerBank.user_id == user_id).count()
        )
        changed = False

        if quantize_amount(target_account.available_amount) != active_count:
            target_account.available_amount = active_count
            changed = True
        if quantize_amount(target_account.total_amount) == Decimal('0.00') and total_bound_count > 0:
            target_account.total_amount = total_bound_count
            changed = True
        if (
            quantize_amount(target_account.consumed_amount) == Decimal('0.00')
            and total_bound_count > active_count
        ):
            target_account.consumed_amount = total_bound_count - active_count
            changed = True
        if changed:
            target_account.updated_at = now()
            if commit:
                db.commit()
                db.refresh(target_account)
            else:
                db.flush()
        return target_account

    @staticmethod
    def active_power_bank_count(db: Session, user_id: int) -> int:
        return int(
            db.query(UserPowerBank).filter(
                UserPowerBank.user_id == user_id,
                UserPowerBank.status == PowerBankStatus.ACTIVE,
            ).count()
        )

    @staticmethod
    def ensure_user_asset_accounts(
        db: Session,
        user_id: int,
        asset_types: list[AssetType] | None = None,
    ) -> bool:
        current_time = now()
        requested_types = AssetService._supported_asset_types(db, asset_types or DEFAULT_ASSET_TYPES)
        existing_types = {
            asset_type
            for (asset_type,) in db.query(UserAssetAccount.asset_type).filter(UserAssetAccount.user_id == user_id).all()
        }
        missing_types = [asset_type for asset_type in requested_types if asset_type not in existing_types]
        for asset_type in missing_types:
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
        if missing_types:
            db.flush()
        return bool(missing_types)

    @staticmethod
    def get_account(db: Session, user_id: int, asset_type: AssetType) -> UserAssetAccount:
        if asset_type == AssetType.POWER_BANK and not AssetService.supports_power_bank_asset_account(db):
            raise NotFoundError('Power bank asset account not supported by current schema')
        if AssetService.ensure_user_asset_accounts(db, user_id, [asset_type]):
            db.commit()
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
    def refund_consumed_amount(
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
        if change <= 0:
            return account
        consumed_before = quantize_amount(account.consumed_amount)
        if consumed_before < change:
            raise ConflictError(f'{asset_type.value} consumed amount insufficient')
        before = quantize_amount(account.available_amount)
        after = before + change
        account.available_amount = after
        account.consumed_amount = consumed_before - change
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
    def revoke_added_amount(
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
        if change <= 0:
            return account
        before = quantize_amount(account.available_amount)
        total_before = quantize_amount(account.total_amount)
        if before < change or total_before < change:
            raise ConflictError(f'{asset_type.value} reward balance insufficient for refund')
        after = before - change
        account.available_amount = after
        account.total_amount = total_before - change
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
    def freeze_amount(
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
        account.frozen_amount = quantize_amount(account.frozen_amount) + change
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
    def unfreeze_amount(
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
        frozen_before = quantize_amount(account.frozen_amount)
        if frozen_before < change:
            raise ConflictError(f'{asset_type.value} frozen amount insufficient')
        before = quantize_amount(account.available_amount)
        after = before + change
        account.available_amount = after
        account.frozen_amount = frozen_before - change
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
    def consume_frozen_amount(
        db: Session,
        user_id: int,
        asset_type: AssetType,
        amount: Decimal | float,
    ) -> UserAssetAccount:
        account = AssetService.get_account(db, user_id, asset_type)
        change = quantize_amount(amount)
        frozen_before = quantize_amount(account.frozen_amount)
        if frozen_before < change:
            raise ConflictError(f'{asset_type.value} frozen amount insufficient')
        account.frozen_amount = frozen_before - change
        account.consumed_amount = quantize_amount(account.consumed_amount) + change
        account.updated_at = now()
        return account

    @staticmethod
    def _serialize_power_bank(power_bank: UserPowerBank) -> dict:
        return {
            'id': power_bank.id,
            'user_id': power_bank.user_id,
            'device_code': power_bank.device_code,
            'device_name': power_bank.device_name,
            'status': power_bank.status.value,
            'bound_at': power_bank.bound_at.isoformat(),
            'last_income_date': power_bank.last_income_date.isoformat() if power_bank.last_income_date else None,
            'total_income_amount': float(power_bank.total_income_amount),
            'total_referral_income_amount': float(power_bank.total_referral_income_amount),
            'remark': power_bank.remark,
            'created_at': power_bank.created_at.isoformat(),
            'updated_at': power_bank.updated_at.isoformat(),
        }

    @staticmethod
    def _update_power_bank_asset_count(
        db: Session,
        user_id: int,
        delta: int,
        business_type: str,
        source_id: int | None = None,
        source_no: str | None = None,
        remark: str | None = None,
    ) -> None:
        if not AssetService.supports_power_bank_asset_account(db):
            return
        if delta > 0:
            AssetService.add_amount(
                db,
                user_id,
                AssetType.POWER_BANK,
                delta,
                business_type,
                source_id=source_id,
                source_no=source_no,
                remark=remark,
            )
        elif delta < 0:
            AssetService.consume_amount(
                db,
                user_id,
                AssetType.POWER_BANK,
                abs(delta),
                business_type,
                source_id=source_id,
                source_no=source_no,
                remark=remark,
            )

    @staticmethod
    def bind_power_bank(
        db: Session,
        user_id: int,
        device_code: str,
        device_name: str | None = None,
        remark: str | None = None,
    ) -> dict:
        if AssetService.ensure_user_asset_accounts(db, user_id):
            db.commit()
        normalized_device_code = (device_code or '').strip().upper()
        if not normalized_device_code:
            raise ConflictError('Device code is required')
        existed = db.query(UserPowerBank).filter(UserPowerBank.device_code == normalized_device_code).first()
        if existed:
            raise ConflictError('Device code already bound')

        current_time = now()
        power_bank = UserPowerBank(
            user_id=user_id,
            device_code=normalized_device_code,
            device_name=(device_name or '').strip() or None,
            status=PowerBankStatus.ACTIVE,
            bound_at=current_time,
            last_income_date=None,
            total_income_amount=0,
            total_referral_income_amount=0,
            remark=(remark or '').strip() or None,
            created_at=current_time,
            updated_at=current_time,
        )
        db.add(power_bank)
        db.flush()
        AssetService._update_power_bank_asset_count(
            db,
            user_id,
            1,
            'POWER_BANK_BIND',
            source_id=power_bank.id,
            source_no=power_bank.device_code,
            remark=power_bank.remark or f'Power bank {power_bank.device_code} bound',
        )
        db.commit()
        db.refresh(power_bank)
        return AssetService._serialize_power_bank(power_bank)

    @staticmethod
    def update_power_bank_status(
        db: Session,
        user_id: int,
        power_bank_id: int,
        status: PowerBankStatus,
    ) -> dict:
        power_bank = db.query(UserPowerBank).filter(
            UserPowerBank.id == power_bank_id,
            UserPowerBank.user_id == user_id,
        ).first()
        if not power_bank:
            raise NotFoundError('Power bank not found')
        if power_bank.status == status:
            return AssetService._serialize_power_bank(power_bank)

        previous_status = power_bank.status
        if previous_status == PowerBankStatus.ACTIVE:
            AssetService.settle_power_bank_income(db, user_id)

        power_bank.status = status
        power_bank.updated_at = now()
        if previous_status != PowerBankStatus.ACTIVE and status == PowerBankStatus.ACTIVE:
            AssetService._update_power_bank_asset_count(
                db,
                user_id,
                1,
                'POWER_BANK_ENABLE',
                source_id=power_bank.id,
                source_no=power_bank.device_code,
                remark=power_bank.remark or f'Power bank {power_bank.device_code} enabled',
            )
        elif previous_status == PowerBankStatus.ACTIVE and status != PowerBankStatus.ACTIVE:
            AssetService._update_power_bank_asset_count(
                db,
                user_id,
                -1,
                'POWER_BANK_DISABLE',
                source_id=power_bank.id,
                source_no=power_bank.device_code,
                remark=power_bank.remark or f'Power bank {power_bank.device_code} disabled',
            )
        db.commit()
        db.refresh(power_bank)
        return AssetService._serialize_power_bank(power_bank)

    @staticmethod
    def settle_power_bank_income(db: Session, user_id: int | None = None) -> None:
        target_date = today()
        query = db.query(UserPowerBank).filter(UserPowerBank.status == PowerBankStatus.ACTIVE)
        if user_id is not None:
            query = query.filter(UserPowerBank.user_id == user_id)
        power_banks = query.order_by(UserPowerBank.id.asc()).all()
        if not power_banks:
            return

        owner_income_amount = EarningRuleService.fixed_amount(db, PB_OWNER_DAILY_RULE, POWER_BANK_OWNER_DAILY_INCOME)
        referrer_income_amount = EarningRuleService.fixed_amount(db, PB_REFERRAL_DAILY_RULE, POWER_BANK_REFERRAL_DAILY_INCOME)

        owner_cache: dict[int, User | None] = {}
        changed = False
        for power_bank in power_banks:
            start_date = power_bank.last_income_date + timedelta(days=1) if power_bank.last_income_date else power_bank.bound_at.date()
            if start_date > target_date:
                continue

            for offset in range((target_date - start_date).days + 1):
                income_date = start_date + timedelta(days=offset)
                existed = db.query(UserPowerBankIncomeRecord).filter(
                    UserPowerBankIncomeRecord.power_bank_id == power_bank.id,
                    UserPowerBankIncomeRecord.income_date == income_date,
                ).first()
                if existed:
                    power_bank.last_income_date = income_date
                    continue

                if power_bank.user_id not in owner_cache:
                    owner_cache[power_bank.user_id] = db.get(User, power_bank.user_id)
                owner = owner_cache[power_bank.user_id]
                if not owner:
                    raise NotFoundError('User not found')

                AssetService.add_amount(
                    db,
                    power_bank.user_id,
                    AssetType.BALANCE,
                    owner_income_amount,
                    'POWER_BANK_DAILY_INCOME',
                    source_id=power_bank.id,
                    source_no=power_bank.device_code,
                    remark=f'Power bank {power_bank.device_code} income {income_date.isoformat()}',
                )

                referrer_income = Decimal('0.00')
                if owner.parent_id:
                    AssetService.add_amount(
                        db,
                        owner.parent_id,
                        AssetType.BALANCE,
                        referrer_income_amount,
                        'POWER_BANK_REFERRAL_INCOME',
                        source_id=power_bank.id,
                        source_no=power_bank.device_code,
                        remark=f'Power bank referral {power_bank.device_code} income {income_date.isoformat()}',
                    )
                    referrer_income = referrer_income_amount

                db.add(
                    UserPowerBankIncomeRecord(
                        power_bank_id=power_bank.id,
                        user_id=power_bank.user_id,
                        referrer_user_id=owner.parent_id,
                        income_date=income_date,
                        owner_income_amount=owner_income_amount,
                        referrer_income_amount=referrer_income,
                        created_at=now(),
                    )
                )
                power_bank.last_income_date = income_date
                power_bank.total_income_amount = quantize_amount(power_bank.total_income_amount) + owner_income_amount
                power_bank.total_referral_income_amount = (
                    quantize_amount(power_bank.total_referral_income_amount) + referrer_income
                )
                power_bank.updated_at = now()
                changed = True

        if changed:
            db.commit()

    @staticmethod
    def list_power_banks(db: Session, user_id: int) -> list[dict]:
        if AssetService.ensure_user_asset_accounts(db, user_id):
            db.commit()
        AssetService.settle_power_bank_income(db, user_id)
        rows = db.query(UserPowerBank).filter(UserPowerBank.user_id == user_id).order_by(UserPowerBank.id.desc()).all()
        return [AssetService._serialize_power_bank(item) for item in rows]

    @staticmethod
    def summary(db: Session, user_id: int) -> dict:
        if AssetService.ensure_user_asset_accounts(db, user_id):
            db.commit()
        AssetService.settle_power_bank_income(db, user_id)
        accounts = db.query(UserAssetAccount).filter(UserAssetAccount.user_id == user_id).all()
        result = {account.asset_type.value: float(account.available_amount) for account in accounts}
        active_power_bank_count = AssetService.active_power_bank_count(db, user_id)
        result['total_amount'] = round(
            sum(float(account.available_amount) for account in accounts if account.asset_type in VISIBLE_ASSET_TOTAL_TYPES),
            2,
        )
        result['POWER_BANK'] = active_power_bank_count
        result['power_bank_count'] = active_power_bank_count
        return result

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
