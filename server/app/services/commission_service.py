from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import String, and_, cast, func, or_
from sqlalchemy.orm import Session, aliased

from app.core.exceptions import ConflictError, NotFoundError
from app.models.bank_card import UserBankCard
from app.models.commission import (
    CommissionAccountLedger,
    CommissionConfig,
    CommissionFlow,
    UserCommission,
    WithdrawRequest,
)
from app.models.enums import (
    CommissionStatus,
    MemberLevel,
    OrderStatus,
    OrderType,
    PayStatus,
    WithdrawStatus,
    WithdrawType,
)
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductZoneConfig
from app.models.team import Team
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.services.catalog_service import ProductService
from app.services.earning_rule_service import EarningRuleService
from app.utils.helpers import iso_datetime, now, quantize_amount
from app.utils.sensitive_data import decrypt_sensitive, mask_bank_card

TEAM_REWARD_FLOW_LEVEL = 100


class CommissionService:
    DEFAULT_WITHDRAW_FEE_RATE = Decimal('0.00')
    DEFAULT_WITHDRAW_MIN_AMOUNT = Decimal('1.00')
    DEFAULT_WITHDRAW_MAX_AMOUNT = Decimal('50000.00')

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
            'updated_at': iso_datetime(item.updated_at),
        }

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
    def withdraw_config(db: Session) -> dict:
        config = db.query(CommissionConfig).order_by(CommissionConfig.id.asc()).first()
        return {
            'fee_rate': float(config.withdraw_fee_rate if config else CommissionService.DEFAULT_WITHDRAW_FEE_RATE),
            'min_amount': float(config.withdraw_min_amount if config else CommissionService.DEFAULT_WITHDRAW_MIN_AMOUNT),
            'max_amount': float(config.withdraw_max_amount if config else CommissionService.DEFAULT_WITHDRAW_MAX_AMOUNT),
        }

    @staticmethod
    def update_withdraw_config(db: Session, fee_rate: float, min_amount: float, max_amount: float, operator_id: int) -> dict:
        rate = quantize_amount(fee_rate)
        minimum = quantize_amount(min_amount)
        maximum = quantize_amount(max_amount)
        if rate < 0 or rate > 100:
            raise ConflictError('Withdraw fee rate must be between 0 and 100')
        if minimum <= 0 or maximum < minimum:
            raise ConflictError('Withdraw amount range is invalid')
        config = db.query(CommissionConfig).order_by(CommissionConfig.id.asc()).with_for_update().first()
        if not config:
            config = CommissionConfig(level1_rate=0, level2_rate=0, is_active=False, updated_at=now())
            db.add(config)
        config.withdraw_fee_rate = rate
        config.withdraw_min_amount = minimum
        config.withdraw_max_amount = maximum
        config.updated_by = operator_id
        config.updated_at = now()
        db.commit()
        return CommissionService.withdraw_config(db)

    @staticmethod
    def create_withdraw(
        db: Session,
        user_id: int,
        withdraw_type: WithdrawType,
        amount: float,
        bank_card_id: int,
        remark: str | None = None,
    ) -> WithdrawRequest:
        quantized = quantize_amount(amount)
        if quantized <= Decimal('0.00'):
            raise ConflictError('Withdraw amount must be greater than 0')
        if withdraw_type != WithdrawType.COMMISSION:
            raise ConflictError('Only commission can be withdrawn')
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError('User not found')

        config = CommissionService.withdraw_config(db)
        minimum = quantize_amount(config['min_amount'])
        maximum = quantize_amount(config['max_amount'])
        if quantized < minimum or quantized > maximum:
            raise ConflictError(f'Withdraw amount must be between {minimum} and {maximum}')
        fee_rate = quantize_amount(config['fee_rate'])
        fee_amount = quantize_amount(quantized * fee_rate / Decimal('100'))
        net_amount = quantized - fee_amount
        if net_amount <= 0:
            raise ConflictError('Withdraw net amount must be greater than 0')

        card = db.query(UserBankCard).filter(
            UserBankCard.id == bank_card_id,
            UserBankCard.user_id == user_id,
        ).with_for_update().first()
        if not card:
            raise NotFoundError('Bank card not found')
        summary = db.query(UserCommission).filter(UserCommission.user_id == user_id).with_for_update().first()
        if not summary or quantize_amount(summary.available_amount) < quantized:
            raise ConflictError('Commission amount insufficient')

        record = WithdrawRequest(
            user_id=user_id,
            team_id=user.team_id,
            withdraw_type=withdraw_type,
            amount=quantized,
            fee_rate=fee_rate,
            fee_amount=fee_amount,
            net_amount=net_amount,
            bank_card_id=card.id,
            bank_holder_name=card.holder_name,
            bank_name=card.bank_name,
            bank_branch_name=card.branch_name,
            bank_card_number_encrypted=card.card_number_encrypted,
            bank_card_last_four=card.card_last_four,
            status=WithdrawStatus.PENDING,
            remark=remark,
            created_at=now(),
        )
        db.add(record)
        db.flush()

        before = CommissionService._commission_balances(summary)
        summary.available_amount = before['available'] - quantized
        summary.frozen_amount = before['frozen'] + quantized
        summary.updated_at = now()
        CommissionService._record_withdraw_ledger(db, summary, record, 'APPLY', before, user_id)

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def list_withdraws(db: Session, user_id: int) -> list[WithdrawRequest]:
        return db.query(WithdrawRequest).filter(
            WithdrawRequest.user_id == user_id,
            WithdrawRequest.withdraw_type == WithdrawType.COMMISSION,
        ).order_by(WithdrawRequest.id.desc()).all()

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
    def list_product_rules_for_admin(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        zone_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 100))
        query = ProductService._admin_product_query(db, current_user).join(
            ProductZoneConfig,
            ProductZoneConfig.product_id == Product.id,
        ).filter(ProductZoneConfig.custom_commission_enabled.is_(True))
        keyword_value = keyword.strip() if keyword else ''
        if keyword_value:
            like_value = f'%{keyword_value}%'
            query = query.filter(or_(
                cast(Product.id, String).ilike(like_value),
                Product.product_name.ilike(like_value),
            ))
        if zone_type:
            query = query.filter(Product.zone_type == zone_type)

        total = int(query.order_by(None).with_entities(func.count(Product.id)).scalar() or 0)
        rows = query.order_by(Product.id.desc()).offset(
            (safe_page - 1) * safe_page_size
        ).limit(safe_page_size).all()
        config_by_product_id = {
            config.product_id: config
            for config in db.query(ProductZoneConfig).filter(
                ProductZoneConfig.product_id.in_([product.id for product in rows])
            ).all()
        } if rows else {}
        return {
            'items': [
                CommissionService.serialize_product_rule(product, config_by_product_id[product.id])
                for product in rows
            ],
            'total': total,
            'page': safe_page,
            'page_size': safe_page_size,
        }

    @staticmethod
    def serialize_product_rule(product: Product, config: ProductZoneConfig) -> dict:
        return {
            'product_id': product.id,
            'product_name': product.product_name,
            'zone_type': product.zone_type.value,
            'method': config.custom_commission_method,
            'level1_enabled': bool(config.custom_commission_level1_enabled),
            'level2_enabled': bool(config.custom_commission_level2_enabled),
            'county_agent_enabled': bool(config.custom_commission_county_agent_enabled),
            'city_agent_enabled': bool(config.custom_commission_city_agent_enabled),
            'level1_rate': float(config.custom_commission_level1_rate or 0),
            'level2_rate': float(config.custom_commission_level2_rate or 0),
            'county_agent_rate': float(config.custom_commission_county_agent_rate or 0),
            'city_agent_rate': float(config.custom_commission_city_agent_rate or 0),
            'level1_amount': float(config.custom_commission_level1_amount or 0),
            'level2_amount': float(config.custom_commission_level2_amount or 0),
            'county_agent_amount': float(config.custom_commission_county_agent_amount or 0),
            'city_agent_amount': float(config.custom_commission_city_agent_amount or 0),
            'updated_at': iso_datetime(config.updated_at),
        }

    @staticmethod
    def list_flows_page_for_admin(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 100))
        beneficiary = aliased(User)
        source = aliased(User)
        query = db.query(CommissionFlow, beneficiary, source, Order).join(
            beneficiary,
            beneficiary.id == CommissionFlow.beneficiary_user_id,
        ).join(
            source,
            source.id == CommissionFlow.source_user_id,
        ).join(Order, Order.id == CommissionFlow.order_id)
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(CommissionFlow.team_id == AdminScopeService.require_team_id(current_user))
        keyword_value = keyword.strip() if keyword else ''
        if keyword_value:
            like_value = f'%{keyword_value}%'
            query = query.filter(or_(
                cast(CommissionFlow.id, String).ilike(like_value),
                cast(CommissionFlow.beneficiary_user_id, String).ilike(like_value),
                cast(CommissionFlow.source_user_id, String).ilike(like_value),
                Order.order_no.ilike(like_value),
                beneficiary.nickname.ilike(like_value),
                beneficiary.phone.ilike(like_value),
                source.nickname.ilike(like_value),
                source.phone.ilike(like_value),
            ))
        if status:
            query = query.filter(CommissionFlow.status == status)

        total = int(query.order_by(None).with_entities(func.count(CommissionFlow.id)).scalar() or 0)
        rows = query.order_by(CommissionFlow.id.desc()).offset(
            (safe_page - 1) * safe_page_size
        ).limit(safe_page_size).all()
        return {
            'items': [
                CommissionService.serialize_admin_flow(flow, beneficiary_user, source_user, order)
                for flow, beneficiary_user, source_user, order in rows
            ],
            'total': total,
            'page': safe_page,
            'page_size': safe_page_size,
        }

    @staticmethod
    def serialize_admin_flow(
        flow: CommissionFlow,
        beneficiary: User,
        source: User,
        order: Order,
    ) -> dict:
        level_label = '直属团队奖励' if flow.level == TEAM_REWARD_FLOW_LEVEL else f'{flow.level}级分润'
        return {
            'id': flow.id,
            'beneficiary_user_id': flow.beneficiary_user_id,
            'beneficiary_nickname': beneficiary.nickname,
            'beneficiary_phone': beneficiary.phone,
            'source_user_id': flow.source_user_id,
            'source_nickname': source.nickname,
            'source_phone': source.phone,
            'order_id': flow.order_id,
            'order_no': order.order_no,
            'level': flow.level,
            'level_label': level_label,
            'rate': float(flow.rate),
            'base_amount': float(flow.base_amount),
            'commission_amount': float(flow.commission_amount),
            'status': flow.status.value,
            'settled_at': iso_datetime(flow.settled_at),
            'created_at': iso_datetime(flow.created_at),
        }

    @staticmethod
    def _admin_withdraw_query(db: Session, current_user: User):
        query = db.query(WithdrawRequest, User, Team).join(User, WithdrawRequest.user_id == User.id).outerjoin(
            Team, WithdrawRequest.team_id == Team.id
        ).filter(WithdrawRequest.withdraw_type == WithdrawType.COMMISSION)
        if not AdminScopeService.has_global_scope(current_user):
            team_id = AdminScopeService.require_team_id(current_user)
            query = query.filter(
                or_(
                    WithdrawRequest.team_id == team_id,
                    and_(WithdrawRequest.team_id.is_(None), User.team_id == team_id),
                )
            )
        return query

    @staticmethod
    def list_withdraws_for_admin(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        query = CommissionService._admin_withdraw_query(db, current_user)
        if keyword and keyword.strip():
            value = f'%{keyword.strip()}%'
            query = query.filter(or_(
                cast(WithdrawRequest.id, String).ilike(value),
                cast(User.id, String).ilike(value),
                User.phone.ilike(value),
                User.nickname.ilike(value),
                WithdrawRequest.bank_holder_name.ilike(value),
            ))
        if status:
            query = query.filter(WithdrawRequest.status == status)
        if start_date:
            query = query.filter(WithdrawRequest.created_at >= datetime.fromisoformat(start_date) - timedelta(hours=8))
        if end_date:
            query = query.filter(WithdrawRequest.created_at < datetime.fromisoformat(end_date) - timedelta(hours=8) + timedelta(days=1))
        total = int(query.order_by(None).with_entities(func.count(WithdrawRequest.id)).scalar() or 0)
        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 100))
        rows = query.order_by(WithdrawRequest.id.desc()).offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
        return {
            'items': [CommissionService.serialize_admin_withdraw(record, user, team) for record, user, team in rows],
            'total': total,
            'page': safe_page,
            'page_size': safe_page_size,
        }

    @staticmethod
    def export_withdraws_for_admin(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        query = CommissionService._admin_withdraw_query(db, current_user)
        if keyword and keyword.strip():
            value = f'%{keyword.strip()}%'
            query = query.filter(or_(
                cast(WithdrawRequest.id, String).ilike(value),
                cast(User.id, String).ilike(value),
                User.phone.ilike(value),
                User.nickname.ilike(value),
                WithdrawRequest.bank_holder_name.ilike(value),
            ))
        if status:
            query = query.filter(WithdrawRequest.status == status)
        if start_date:
            query = query.filter(WithdrawRequest.created_at >= datetime.fromisoformat(start_date) - timedelta(hours=8))
        if end_date:
            query = query.filter(WithdrawRequest.created_at < datetime.fromisoformat(end_date) - timedelta(hours=8) + timedelta(days=1))
        return [CommissionService.serialize_admin_withdraw(record, user, team, include_card_number=True) for record, user, team in query.order_by(WithdrawRequest.id.desc()).all()]

    @staticmethod
    def serialize_admin_withdraw(record: WithdrawRequest, user: User, team: Team | None, include_card_number: bool = False) -> dict:
        data = {
            'id': record.id,
            'source_no': CommissionService._withdraw_source_no(record.id),
            'user_id': user.id,
            'user_nickname': user.nickname,
            'user_phone': user.phone,
            'team_id': record.team_id,
            'team_name': team.name if team else None,
            'withdraw_type': record.withdraw_type.value,
            'amount': float(record.amount),
            'fee_rate': float(record.fee_rate or 0),
            'fee_amount': float(record.fee_amount or 0),
            'net_amount': float(record.net_amount or record.amount),
            'bank_holder_name': record.bank_holder_name,
            'bank_name': record.bank_name,
            'bank_branch_name': record.bank_branch_name,
            'bank_card_last_four': record.bank_card_last_four,
            'masked_bank_card_number': mask_bank_card(record.bank_card_last_four) if record.bank_card_last_four else None,
            'status': record.status.value,
            'remark': record.remark,
            'review_remark': record.review_remark,
            'reviewed_by': record.reviewed_by,
            'reviewed_at': iso_datetime(record.reviewed_at),
            'paid_by': record.paid_by,
            'paid_at': iso_datetime(record.paid_at),
            'created_at': iso_datetime(record.created_at),
        }
        if include_card_number:
            data['bank_card_number'] = decrypt_sensitive(record.bank_card_number_encrypted) if record.bank_card_number_encrypted else ''
        return data

    @staticmethod
    def _commission_balances(summary: UserCommission) -> dict[str, Decimal]:
        return {
            'available': quantize_amount(summary.available_amount),
            'frozen': quantize_amount(summary.frozen_amount),
            'withdrawn': quantize_amount(summary.withdrawn_amount),
        }

    @staticmethod
    def _record_withdraw_ledger(
        db: Session,
        summary: UserCommission,
        record: WithdrawRequest,
        action: str,
        before: dict[str, Decimal],
        operator_id: int | None,
    ) -> None:
        after = CommissionService._commission_balances(summary)
        db.add(CommissionAccountLedger(
            user_id=record.user_id,
            withdraw_request_id=record.id,
            action=action,
            amount=quantize_amount(record.amount),
            available_before=before['available'],
            available_after=after['available'],
            frozen_before=before['frozen'],
            frozen_after=after['frozen'],
            withdrawn_before=before['withdrawn'],
            withdrawn_after=after['withdrawn'],
            operator_id=operator_id,
            created_at=now(),
        ))

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
        matched_custom_roles: dict[int, set[str]] = {}
        for level, beneficiary in ancestors:
            if not CommissionService._distribution_enabled(db, beneficiary):
                continue
            for product_id, base_amount, quantity in profit_items:
                custom_config = custom_configs.get(product_id)
                if custom_config:
                    role = CommissionService._custom_commission_member_role(beneficiary.member_level)
                    if not role or role in matched_custom_roles.setdefault(product_id, set()):
                        continue
                    matched_custom_roles[product_id].add(role)
                    rate, fixed_amount = CommissionService._custom_commission_value(
                        custom_config,
                        beneficiary.member_level,
                        quantity,
                    )
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
                rate, fixed_amount = CommissionService._custom_commission_value(
                    custom_config,
                    beneficiary.member_level,
                    quantity,
                )
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
        rate = EarningRuleService.rate_for_team_member_level(db, beneficiary.member_level)
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
        member_level: MemberLevel | str,
        quantity: Decimal,
    ) -> tuple[Decimal, Decimal | None]:
        role = CommissionService._custom_commission_member_role(member_level)
        if not role:
            return Decimal('0'), None
        if not bool(getattr(config, f'custom_commission_{role}_enabled', False)):
            return Decimal('0'), None
        if str(config.custom_commission_method or 'RATE').upper() == 'FIXED_AMOUNT':
            unit_amount = Decimal(str(getattr(config, f'custom_commission_{role}_amount', 0) or 0))
            return Decimal('0'), quantize_amount(unit_amount * quantity)
        percentage = Decimal(str(getattr(config, f'custom_commission_{role}_rate', 0) or 0))
        return percentage / Decimal('100'), None

    @staticmethod
    def _custom_commission_member_role(member_level: MemberLevel | str) -> str | None:
        normalized = str(member_level or '').strip().upper()
        return {
            MemberLevel.NORMAL_MEMBER.value: 'level1',
            MemberLevel.DEALER.value: 'level2',
        }.get(normalized)

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
        if user.member_level in {
            MemberLevel.DEALER,
            MemberLevel.COUNTY_AGENT,
            MemberLevel.CITY_AGENT,
        }:
            return True
        return db.query(Order.id).filter(
            Order.user_id == user.id,
            Order.pay_status == PayStatus.PAID,
            Order.order_status.notin_([OrderStatus.REFUND]),
        ).first() is not None

    @staticmethod
    def approve_withdraw(db: Session, withdraw_id: int, current_user: User, remark: str | None = None) -> WithdrawRequest:
        record = db.query(WithdrawRequest).filter(WithdrawRequest.id == withdraw_id).with_for_update().first()
        if not record:
            raise NotFoundError('Withdraw request not found')
        if record.status != WithdrawStatus.PENDING:
            raise ConflictError('Withdraw status invalid')
        CommissionService._ensure_withdraw_visible(db, record, current_user)
        if record.withdraw_type != WithdrawType.COMMISSION:
            raise ConflictError('Only commission withdraw requests can be reviewed')
        if not record.bank_card_number_encrypted:
            raise ConflictError('Withdraw request does not contain bank card information')

        record.status = WithdrawStatus.APPROVED
        record.reviewed_by = current_user.id
        record.reviewed_at = now()
        record.review_remark = remark
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def reject_withdraw(db: Session, withdraw_id: int, current_user: User, remark: str | None = None) -> WithdrawRequest:
        record = db.query(WithdrawRequest).filter(WithdrawRequest.id == withdraw_id).with_for_update().first()
        if not record:
            raise NotFoundError('Withdraw request not found')
        if record.status != WithdrawStatus.PENDING:
            raise ConflictError('Withdraw status invalid')
        CommissionService._ensure_withdraw_visible(db, record, current_user)

        if record.withdraw_type != WithdrawType.COMMISSION:
            raise ConflictError('Only commission withdraw requests can be reviewed')
        amount = quantize_amount(record.amount)
        summary = db.query(UserCommission).filter(UserCommission.user_id == record.user_id).with_for_update().first()
        if not summary or quantize_amount(summary.frozen_amount) < amount:
            raise ConflictError('Commission frozen amount insufficient')
        before = CommissionService._commission_balances(summary)
        summary.frozen_amount = before['frozen'] - amount
        summary.available_amount = before['available'] + amount
        summary.updated_at = now()
        CommissionService._record_withdraw_ledger(db, summary, record, 'REJECT', before, current_user.id)

        record.status = WithdrawStatus.REJECTED
        record.reviewed_by = current_user.id
        record.reviewed_at = now()
        record.review_remark = remark
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def pay_withdraw(db: Session, withdraw_id: int, current_user: User) -> WithdrawRequest:
        record = db.query(WithdrawRequest).filter(WithdrawRequest.id == withdraw_id).with_for_update().first()
        if not record:
            raise NotFoundError('Withdraw request not found')
        if record.status != WithdrawStatus.APPROVED:
            raise ConflictError('Only approved withdraw requests can be paid')
        CommissionService._ensure_withdraw_visible(db, record, current_user)
        if record.withdraw_type != WithdrawType.COMMISSION:
            raise ConflictError('Only commission withdraw requests can be paid')
        amount = quantize_amount(record.amount)
        summary = db.query(UserCommission).filter(UserCommission.user_id == record.user_id).with_for_update().first()
        if not summary or quantize_amount(summary.frozen_amount) < amount:
            raise ConflictError('Commission frozen amount insufficient')
        before = CommissionService._commission_balances(summary)
        summary.frozen_amount = before['frozen'] - amount
        summary.withdrawn_amount = before['withdrawn'] + amount
        summary.updated_at = now()
        CommissionService._record_withdraw_ledger(db, summary, record, 'PAY', before, current_user.id)
        record.status = WithdrawStatus.PAID
        record.paid_by = current_user.id
        record.paid_at = now()
        db.commit()
        db.refresh(record)
        return record
