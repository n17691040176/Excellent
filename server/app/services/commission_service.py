from decimal import Decimal

from sqlalchemy import String, and_, cast, func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.asset import UserAssetLedger
from app.models.commission import CommissionConfig, CommissionFlow, UserCommission, WithdrawRequest
from app.models.enums import (
    AssetType,
    BusinessIdentity,
    CommissionStatus,
    OrderStatus,
    OrderType,
    PayStatus,
    WithdrawStatus,
    WithdrawType,
)
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductZoneConfig
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import AssetService
from app.services.earning_rule_service import EarningRuleService
from app.utils.helpers import now, quantize_amount

BALANCE_WITHDRAW_VOUCHER_RATE = Decimal('0.20')
TEAM_REWARD_FLOW_LEVEL = 100
BALANCE_WITHDRAW_APPLY = 'BALANCE_WITHDRAW_APPLY'
BALANCE_WITHDRAW_REJECT = 'BALANCE_WITHDRAW_REJECT'
POINTS_WITHDRAW_APPLY = 'POINTS_WITHDRAW_APPLY'
POINTS_WITHDRAW_REJECT = 'POINTS_WITHDRAW_REJECT'


class CommissionService:
    @staticmethod
    def _admin_user_commission_query(
        db: Session,
        current_user: User,
        keyword: str | None = None,
    ):
        query = db.query(UserCommission).join(User, User.id == UserCommission.user_id)
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(User.team_id == AdminScopeService.require_team_id(current_user))
        keyword_value = keyword.strip() if keyword else ''
        if keyword_value:
            like_value = f'%{keyword_value}%'
            query = query.filter(or_(
                cast(UserCommission.user_id, String).ilike(like_value),
                User.phone.ilike(like_value),
                User.nickname.ilike(like_value),
                User.real_name.ilike(like_value),
                User.invite_code.ilike(like_value),
            ))
        return query

    @staticmethod
    def serialize_admin_user_commission(item: UserCommission) -> dict:
        return {
            'id': item.id,
            'user_id': item.user_id,
            'available_amount': float(item.available_amount),
            'frozen_amount': float(item.frozen_amount),
            'withdrawn_amount': float(item.withdrawn_amount),
            'total_amount': float(item.total_amount),
            'updated_at': item.updated_at,
        }

    @staticmethod
    def get_config(db: Session) -> CommissionConfig:
        config = db.query(CommissionConfig).order_by(CommissionConfig.id.desc()).first()
        if not config:
            config = CommissionConfig(level1_rate=0, level2_rate=0, is_active=False, updated_at=now())
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    @staticmethod
    def summary(db: Session, user_id: int) -> dict:
        data = db.query(UserCommission).filter(UserCommission.user_id == user_id).first()
        if not data:
            return {'frozen_amount': 0, 'available_amount': 0, 'total_amount': 0, 'withdrawn_amount': 0}
        return {
            'frozen_amount': float(data.frozen_amount),
            'available_amount': float(data.available_amount),
            'total_amount': float(data.total_amount),
            'withdrawn_amount': float(data.withdrawn_amount),
        }

    @staticmethod
    def flows(db: Session, user_id: int) -> list[CommissionFlow]:
        return db.query(CommissionFlow).filter(CommissionFlow.beneficiary_user_id == user_id).order_by(CommissionFlow.id.desc()).all()

    @staticmethod
    def freeze_for_order(db: Session, order: Order, buyer: User) -> None:
        if db.query(CommissionFlow.id).filter(CommissionFlow.order_id == order.id).first():
            return

        profit_items = CommissionService._order_profit_items(db, order.id)
        if not profit_items:
            return

        custom_configs = CommissionService._custom_commission_configs(db, profit_items)

        if order.order_type == OrderType.REPURCHASE_ORDER:
            CommissionService._freeze_repurchase_reward(db, order, buyer, profit_items, custom_configs)
        else:
            CommissionService._freeze_distribution_rewards(db, order, buyer, profit_items, custom_configs)
        standard_profit_items = [item for item in profit_items if item[0] not in custom_configs]
        CommissionService._freeze_direct_team_reward(db, order, buyer, standard_profit_items)

    @staticmethod
    def settle_for_order(db: Session, order_id: int) -> None:
        flows = db.query(CommissionFlow).filter(
            CommissionFlow.order_id == order_id,
            CommissionFlow.status == CommissionStatus.FROZEN,
        ).all()
        for flow in flows:
            summary = db.query(UserCommission).filter(UserCommission.user_id == flow.beneficiary_user_id).first()
            if not summary:
                continue
            amount = quantize_amount(flow.commission_amount)
            summary.frozen_amount = quantize_amount(summary.frozen_amount) - amount
            summary.available_amount = quantize_amount(summary.available_amount) + amount
            summary.updated_at = now()
            flow.status = CommissionStatus.SETTLED
            flow.settled_at = now()
        db.commit()

    @staticmethod
    def cancel_for_order(db: Session, order_id: int) -> None:
        flows = db.query(CommissionFlow).filter(
            CommissionFlow.order_id == order_id,
            CommissionFlow.status.in_([CommissionStatus.FROZEN, CommissionStatus.SETTLED]),
        ).all()
        for flow in flows:
            summary = db.query(UserCommission).filter(UserCommission.user_id == flow.beneficiary_user_id).first()
            if not summary:
                flow.status = CommissionStatus.CANCELED
                continue
            amount = quantize_amount(flow.commission_amount)
            if flow.status == CommissionStatus.FROZEN:
                summary.frozen_amount = max(quantize_amount(summary.frozen_amount) - amount, Decimal('0.00'))
            else:
                available = quantize_amount(summary.available_amount)
                if available < amount:
                    raise ConflictError('Settled commission balance is insufficient for refund')
                summary.available_amount = available - amount
            summary.total_amount = max(quantize_amount(summary.total_amount) - amount, Decimal('0.00'))
            summary.updated_at = now()
            flow.status = CommissionStatus.CANCELED
        db.flush()

    @staticmethod
    def create_withdraw(db: Session, user_id: int, withdraw_type: WithdrawType, amount: float, remark: str | None = None) -> WithdrawRequest:
        quantized = quantize_amount(amount)
        if quantized <= Decimal('0.00'):
            raise ConflictError('Withdraw amount must be greater than 0')
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError('User not found')

        summary = None
        if withdraw_type == WithdrawType.COMMISSION:
            summary = db.query(UserCommission).filter(UserCommission.user_id == user_id).first()
            if not summary or quantize_amount(summary.available_amount) < quantized:
                raise ConflictError('Commission amount insufficient')
        else:
            asset_type, _, _ = CommissionService._asset_withdraw_meta(withdraw_type)
            account = AssetService.get_account(db, user_id, asset_type)
            if quantize_amount(account.available_amount) < quantized:
                raise ConflictError('Asset amount insufficient')

        record = WithdrawRequest(
            user_id=user_id,
            team_id=user.team_id,
            withdraw_type=withdraw_type,
            amount=quantized,
            status=WithdrawStatus.PENDING,
            remark=remark,
            created_at=now(),
        )
        db.add(record)
        db.flush()

        source_no = CommissionService._withdraw_source_no(record.id)
        if withdraw_type == WithdrawType.COMMISSION:
            assert summary is not None
            summary.available_amount = quantize_amount(summary.available_amount) - quantized
            summary.frozen_amount = quantize_amount(summary.frozen_amount) + quantized
            summary.updated_at = now()
        else:
            asset_type, apply_business_type, _ = CommissionService._asset_withdraw_meta(withdraw_type)
            AssetService.freeze_amount(
                db,
                user_id,
                asset_type,
                quantized,
                apply_business_type,
                source_id=record.id,
                source_no=source_no,
            )

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def list_withdraws(db: Session, user_id: int) -> list[WithdrawRequest]:
        return db.query(WithdrawRequest).filter(WithdrawRequest.user_id == user_id).order_by(WithdrawRequest.id.desc()).all()

    @staticmethod
    def list_user_commissions_page_for_admin(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 100))
        query = CommissionService._admin_user_commission_query(db, current_user, keyword=keyword)

        total = int(query.order_by(None).with_entities(func.count(UserCommission.id)).scalar() or 0)
        summary_row = query.order_by(None).with_entities(
            func.coalesce(func.sum(UserCommission.available_amount), 0),
            func.coalesce(func.sum(UserCommission.frozen_amount), 0),
            func.coalesce(func.sum(UserCommission.withdrawn_amount), 0),
            func.coalesce(func.sum(UserCommission.total_amount), 0),
        ).one()
        rows = query.order_by(UserCommission.id.desc()).offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()

        return {
            'items': [CommissionService.serialize_admin_user_commission(item) for item in rows],
            'total': total,
            'page': safe_page,
            'page_size': safe_page_size,
            'summary': {
                'user_count': total,
                'available_amount': float(summary_row[0] or 0),
                'frozen_amount': float(summary_row[1] or 0),
                'withdrawn_amount': float(summary_row[2] or 0),
                'total_amount': float(summary_row[3] or 0),
            },
        }

    @staticmethod
    def list_flows_for_admin(db: Session, current_user: User) -> list[CommissionFlow]:
        query = db.query(CommissionFlow)
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(CommissionFlow.team_id == AdminScopeService.require_team_id(current_user))
        return query.order_by(CommissionFlow.id.desc()).all()

    @staticmethod
    def list_withdraws_for_admin(db: Session, current_user: User) -> list[WithdrawRequest]:
        query = db.query(WithdrawRequest)
        if not AdminScopeService.has_global_scope(current_user):
            team_id = AdminScopeService.require_team_id(current_user)
            query = query.outerjoin(User, WithdrawRequest.user_id == User.id).filter(
                or_(
                    WithdrawRequest.team_id == team_id,
                    and_(WithdrawRequest.team_id.is_(None), User.team_id == team_id),
                )
            )
        return query.order_by(WithdrawRequest.id.desc()).all()

    @staticmethod
    def _ensure_withdraw_visible(db: Session, record: WithdrawRequest, current_user: User) -> None:
        if AdminScopeService.has_global_scope(current_user):
            return
        scoped_team_id = AdminScopeService.require_team_id(current_user)
        record_team_id = record.team_id
        if record_team_id is None:
            target_user = db.get(User, record.user_id)
            record_team_id = target_user.team_id if target_user else None
        if record_team_id != scoped_team_id:
            raise ConflictError('Withdraw request out of team scope')

    @staticmethod
    def _withdraw_source_no(withdraw_id: int) -> str:
        return f'WD-{withdraw_id}'

    @staticmethod
    def _freeze_distribution_rewards(
        db: Session,
        order: Order,
        buyer: User,
        profit_items: list[tuple[int, Decimal, Decimal]],
        custom_configs: dict[int, ProductZoneConfig],
    ) -> None:
        ancestors = CommissionService._ancestor_users(db, buyer, max_level=3)
        for level, beneficiary in ancestors:
            if not CommissionService._distribution_enabled(db, beneficiary):
                continue
            for product_id, base_amount, quantity in profit_items:
                custom_config = custom_configs.get(product_id)
                if custom_config:
                    rate, fixed_amount = CommissionService._custom_commission_value(custom_config, level, quantity)
                else:
                    rate = EarningRuleService.rate_for_commission_level(
                        db,
                        level,
                        product_id=product_id,
                        trigger_event='ORDER_COMPLETE',
                    )
                    fixed_amount = None
                CommissionService._add_frozen_flow(
                    db,
                    order,
                    buyer,
                    beneficiary,
                    level,
                    rate,
                    base_amount,
                    commission_amount=fixed_amount,
                )

    @staticmethod
    def _freeze_repurchase_reward(
        db: Session,
        order: Order,
        buyer: User,
        profit_items: list[tuple[int, Decimal, Decimal]],
        custom_configs: dict[int, ProductZoneConfig],
    ) -> None:
        if not buyer.parent_id:
            return
        beneficiary = db.get(User, buyer.parent_id)
        if not beneficiary or not CommissionService._distribution_enabled(db, beneficiary):
            return
        for product_id, base_amount, quantity in profit_items:
            custom_config = custom_configs.get(product_id)
            if custom_config:
                rate, fixed_amount = CommissionService._custom_commission_value(custom_config, 1, quantity)
            else:
                rate = EarningRuleService.rate_for_commission_level(
                    db,
                    1,
                    product_id=product_id,
                    trigger_event='REPEAT_PURCHASE',
                )
                fixed_amount = None
            CommissionService._add_frozen_flow(
                db,
                order,
                buyer,
                beneficiary,
                1,
                rate,
                base_amount,
                commission_amount=fixed_amount,
            )

    @staticmethod
    def _freeze_direct_team_reward(
        db: Session,
        order: Order,
        buyer: User,
        profit_items: list[tuple[int, Decimal, Decimal]],
    ) -> None:
        if not profit_items:
            return
        if not buyer.parent_id:
            return
        beneficiary = db.get(User, buyer.parent_id)
        if not beneficiary or not CommissionService._distribution_enabled(db, beneficiary):
            return
        rate = EarningRuleService.rate_for_team_member_level(db, beneficiary.business_identity)
        total_profit = quantize_amount(sum((amount for _, amount, _ in profit_items), Decimal('0')))
        CommissionService._add_frozen_flow(db, order, buyer, beneficiary, TEAM_REWARD_FLOW_LEVEL, rate, total_profit)

    @staticmethod
    def _add_frozen_flow(
        db: Session,
        order: Order,
        buyer: User,
        beneficiary: User,
        level: int,
        rate: Decimal,
        base_amount: Decimal,
        commission_amount: Decimal | None = None,
    ) -> None:
        base = quantize_amount(base_amount)
        if commission_amount is None:
            if base <= Decimal('0') or rate <= Decimal('0'):
                return
            amount = quantize_amount(base * rate)
        else:
            amount = quantize_amount(commission_amount)
        if amount <= Decimal('0'):
            return
        commission = db.query(UserCommission).filter(UserCommission.user_id == beneficiary.id).first()
        if not commission:
            commission = UserCommission(user_id=beneficiary.id, updated_at=now())
            db.add(commission)
            db.flush()
        commission.frozen_amount = quantize_amount(commission.frozen_amount) + amount
        commission.total_amount = quantize_amount(commission.total_amount) + amount
        commission.updated_at = now()
        db.add(
            CommissionFlow(
                beneficiary_user_id=beneficiary.id,
                source_user_id=buyer.id,
                order_id=order.id,
                team_id=buyer.team_id,
                level=level,
                rate=quantize_amount(rate * Decimal('100')),
                base_amount=base,
                commission_amount=amount,
                status=CommissionStatus.FROZEN,
                created_at=now(),
            )
        )

    @staticmethod
    def _order_profit_items(db: Session, order_id: int) -> list[tuple[int, Decimal, Decimal]]:
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        if not items:
            return []
        product_ids = {item.product_id for item in items}
        products = {
            product.id: product
            for product in db.query(Product).filter(Product.id.in_(product_ids)).all()
        }
        profit_items: list[tuple[int, Decimal, Decimal]] = []
        for item in items:
            product = products.get(item.product_id)
            quantity = Decimal(str(item.quantity or 0))
            if not product or product.cost_price is None:
                profit = Decimal('0')
            else:
                unit_price = Decimal(str(item.unit_price or '0'))
                cost_price = Decimal(str(product.cost_price or '0'))
                profit = max(Decimal('0'), unit_price - cost_price) * quantity
            profit_items.append((item.product_id, quantize_amount(profit), quantity))
        return profit_items

    @staticmethod
    def _custom_commission_configs(
        db: Session,
        profit_items: list[tuple[int, Decimal, Decimal]],
    ) -> dict[int, ProductZoneConfig]:
        product_ids = {product_id for product_id, _, _ in profit_items}
        if not product_ids:
            return {}
        rows = db.query(ProductZoneConfig).filter(
            ProductZoneConfig.product_id.in_(product_ids),
            ProductZoneConfig.custom_commission_enabled.is_(True),
        ).all()
        return {row.product_id: row for row in rows}

    @staticmethod
    def _custom_commission_value(
        config: ProductZoneConfig,
        level: int,
        quantity: Decimal,
    ) -> tuple[Decimal, Decimal | None]:
        if level < 1 or level > 3:
            return Decimal('0'), None
        if str(config.custom_commission_method or 'RATE').upper() == 'FIXED_AMOUNT':
            unit_amount = Decimal(str(getattr(config, f'custom_commission_level{level}_amount', 0) or 0))
            return Decimal('0'), quantize_amount(unit_amount * quantity)
        percentage = Decimal(str(getattr(config, f'custom_commission_level{level}_rate', 0) or 0))
        return percentage / Decimal('100'), None

    @staticmethod
    def _ancestor_users(db: Session, buyer: User, max_level: int) -> list[tuple[int, User]]:
        ancestors: list[tuple[int, User]] = []
        next_user_id = buyer.parent_id
        level = 1
        visited: set[int] = {buyer.id}
        while next_user_id and level <= max_level and next_user_id not in visited:
            user = db.get(User, next_user_id)
            if not user:
                break
            ancestors.append((level, user))
            visited.add(user.id)
            next_user_id = user.parent_id
            level += 1
        return ancestors

    @staticmethod
    def _distribution_enabled(db: Session, user: User) -> bool:
        if user.business_identity in {
            BusinessIdentity.VIP_MEMBER,
            BusinessIdentity.DEALER,
            BusinessIdentity.MASTER_DEALER,
        }:
            return True
        if user.business_identity != BusinessIdentity.NORMAL_MEMBER:
            return False
        return db.query(Order.id).filter(
            Order.user_id == user.id,
            Order.pay_status == PayStatus.PAID,
            Order.order_status.notin_([OrderStatus.REFUND]),
        ).first() is not None

    @staticmethod
    def _asset_withdraw_meta(withdraw_type: WithdrawType) -> tuple[AssetType, str, str]:
        if withdraw_type == WithdrawType.BALANCE:
            return AssetType.BALANCE, BALANCE_WITHDRAW_APPLY, BALANCE_WITHDRAW_REJECT
        if withdraw_type == WithdrawType.POINTS:
            return AssetType.POINTS, POINTS_WITHDRAW_APPLY, POINTS_WITHDRAW_REJECT
        raise ConflictError('Withdraw type invalid')

    @staticmethod
    def _asset_withdraw_reserved(db: Session, record: WithdrawRequest) -> bool:
        if record.withdraw_type not in {WithdrawType.BALANCE, WithdrawType.POINTS}:
            return False
        _, apply_business_type, _ = CommissionService._asset_withdraw_meta(record.withdraw_type)
        return db.query(UserAssetLedger.id).filter(
            UserAssetLedger.user_id == record.user_id,
            UserAssetLedger.source_id == record.id,
            UserAssetLedger.business_type == apply_business_type,
        ).first() is not None

    @staticmethod
    def approve_withdraw(db: Session, withdraw_id: int, current_user: User) -> WithdrawRequest:
        record = db.get(WithdrawRequest, withdraw_id)
        if not record:
            raise NotFoundError('Withdraw request not found')
        if record.status != WithdrawStatus.PENDING:
            raise ConflictError('Withdraw status invalid')
        CommissionService._ensure_withdraw_visible(db, record, current_user)

        amount = quantize_amount(record.amount)
        if record.withdraw_type == WithdrawType.COMMISSION:
            summary = db.query(UserCommission).filter(UserCommission.user_id == record.user_id).first()
            if not summary:
                raise ConflictError('Commission amount insufficient')
            reserved_amount = quantize_amount(summary.frozen_amount)
            available_amount = quantize_amount(summary.available_amount)
            if reserved_amount >= amount:
                summary.frozen_amount = reserved_amount - amount
            elif available_amount >= amount:
                summary.available_amount = available_amount - amount
            else:
                raise ConflictError('Commission amount insufficient')
            summary.withdrawn_amount = quantize_amount(summary.withdrawn_amount) + amount
            summary.updated_at = now()
        else:
            asset_type, _, _ = CommissionService._asset_withdraw_meta(record.withdraw_type)
            account_reserved = CommissionService._asset_withdraw_reserved(db, record)
            source_no = CommissionService._withdraw_source_no(record.id)

            if record.withdraw_type == WithdrawType.BALANCE:
                voucher_amount = quantize_amount(amount * BALANCE_WITHDRAW_VOUCHER_RATE)
                net_amount = quantize_amount(amount - voucher_amount)
                if account_reserved:
                    account = AssetService.consume_frozen_amount(db, record.user_id, asset_type, amount)
                else:
                    account = AssetService.consume_amount(
                        db,
                        record.user_id,
                        asset_type,
                        amount,
                        'BALANCE_WITHDRAW_APPROVE',
                        source_id=record.id,
                        source_no=source_no,
                    )
                AssetService.add_amount(
                    db,
                    record.user_id,
                    AssetType.VOUCHER,
                    voucher_amount,
                    'BALANCE_WITHDRAW_VOUCHER',
                    source_id=record.id,
                    source_no=source_no,
                )
                account.withdrawn_amount = quantize_amount(account.withdrawn_amount) + net_amount
            else:
                if account_reserved:
                    account = AssetService.consume_frozen_amount(db, record.user_id, asset_type, amount)
                else:
                    account = AssetService.consume_amount(
                        db,
                        record.user_id,
                        asset_type,
                        amount,
                        'POINTS_WITHDRAW_APPROVE',
                        source_id=record.id,
                        source_no=source_no,
                    )
                account.withdrawn_amount = quantize_amount(account.withdrawn_amount) + amount
            account.updated_at = now()

        record.status = WithdrawStatus.APPROVED
        record.reviewed_by = current_user.id
        record.reviewed_at = now()
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def reject_withdraw(db: Session, withdraw_id: int, current_user: User, remark: str | None = None) -> WithdrawRequest:
        record = db.get(WithdrawRequest, withdraw_id)
        if not record:
            raise NotFoundError('Withdraw request not found')
        if record.status != WithdrawStatus.PENDING:
            raise ConflictError('Withdraw status invalid')
        CommissionService._ensure_withdraw_visible(db, record, current_user)

        amount = quantize_amount(record.amount)
        if record.withdraw_type == WithdrawType.COMMISSION:
            summary = db.query(UserCommission).filter(UserCommission.user_id == record.user_id).first()
            if summary and quantize_amount(summary.frozen_amount) >= amount:
                summary.frozen_amount = quantize_amount(summary.frozen_amount) - amount
                summary.available_amount = quantize_amount(summary.available_amount) + amount
                summary.updated_at = now()
        elif CommissionService._asset_withdraw_reserved(db, record):
            asset_type, _, reject_business_type = CommissionService._asset_withdraw_meta(record.withdraw_type)
            AssetService.unfreeze_amount(
                db,
                record.user_id,
                asset_type,
                amount,
                reject_business_type,
                source_id=record.id,
                source_no=CommissionService._withdraw_source_no(record.id),
            )

        record.status = WithdrawStatus.REJECTED
        record.reviewed_by = current_user.id
        record.reviewed_at = now()
        if remark:
            record.remark = remark
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def pay_withdraw(db: Session, withdraw_id: int, current_user: User) -> WithdrawRequest:
        record = db.get(WithdrawRequest, withdraw_id)
        if not record:
            raise NotFoundError('Withdraw request not found')
        if record.status != WithdrawStatus.APPROVED:
            raise ConflictError('Only approved withdraw requests can be paid')
        CommissionService._ensure_withdraw_visible(db, record, current_user)
        record.status = WithdrawStatus.PAID
        record.paid_by = current_user.id
        record.paid_at = now()
        db.commit()
        db.refresh(record)
        return record
