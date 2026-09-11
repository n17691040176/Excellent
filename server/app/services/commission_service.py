from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, and_, case, cast, func, literal, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.exceptions import ConflictError, NotFoundError
from app.models.address import UserAddress
from app.models.bank_card import UserBankCard
from app.models.city_partner import CityPartnerCommissionFlow, CityPartnerSeat
from app.models.commission import (
    CommissionAccountLedger,
    CommissionConfig,
    CommissionFlow,
    CommissionModeSwitchLog,
    UserCommission,
    WithdrawRequest,
)
from app.models.enums import (
    CommissionMode,
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
from app.models.region_dividend import RegionDividendFlow
from app.models.team import Team
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.services.catalog_service import ProductService
from app.services.city_partner_rules import (
    CityPartnerSettlementError,
    city_partner_rule_values,
    upline_calculations,
    validate_city_partner_rule,
)
from app.services.commission_accounts import system_account
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
        original = db.query(CommissionFlow).filter(CommissionFlow.beneficiary_user_id == user_id).all()
        city = db.query(CityPartnerCommissionFlow).filter(CityPartnerCommissionFlow.beneficiary_user_id == user_id).all()
        return sorted([*original, *city], key=lambda flow: (flow.created_at, flow.id), reverse=True)

    @staticmethod
    def freeze_for_order(db: Session, order: Order, buyer: User) -> None:
        CommissionService.assert_fulfillable(order)
        CommissionService.assert_mode_isolation(db, order)
        mode = getattr(order, 'commission_mode', None) or CommissionService._current_mode(db)
        if mode == CommissionMode.CITY_PARTNER:
            CommissionService._freeze_city_partner_rewards(db, order, buyer)
            return
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
    def settle_for_order(db: Session, order_id: int, *, commit: bool = True) -> None:
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            return
        db.refresh(order, with_for_update=True)
        CommissionService.assert_fulfillable(order)
        CommissionService.assert_mode_isolation(db, order)
        if order.pay_status != PayStatus.PAID or order.order_status != OrderStatus.COMPLETED:
            return
        flows = db.query(CommissionFlow).filter(
            CommissionFlow.order_id == order_id,
            CommissionFlow.status == CommissionStatus.FROZEN,
        ).order_by(CommissionFlow.id.asc()).populate_existing().with_for_update().all()
        for flow in flows:
            summary = db.query(UserCommission).filter(
                UserCommission.user_id == flow.beneficiary_user_id
            ).populate_existing().with_for_update().first()
            if not summary:
                continue
            amount = quantize_amount(flow.commission_amount)
            summary.frozen_amount = quantize_amount(summary.frozen_amount) - amount
            summary.available_amount = quantize_amount(summary.available_amount) + amount
            summary.updated_at = now()
            flow.status = CommissionStatus.SETTLED
            flow.settled_at = now()
            db.flush()
        city_flows = db.query(CityPartnerCommissionFlow).filter(
            CityPartnerCommissionFlow.order_id == order_id,
            CityPartnerCommissionFlow.status == CommissionStatus.FROZEN,
        ).order_by(CityPartnerCommissionFlow.beneficiary_user_id.asc(), CityPartnerCommissionFlow.id.asc()).populate_existing().with_for_update().all()
        for flow in city_flows:
            if flow.beneficiary_user_id is None:
                flow.status = CommissionStatus.SETTLED
                flow.settled_at = now()
                continue
            summary = db.query(UserCommission).filter(UserCommission.user_id == flow.beneficiary_user_id).populate_existing().with_for_update().first()
            if not summary:
                continue
            amount = quantize_amount(flow.commission_amount)
            summary.frozen_amount = quantize_amount(summary.frozen_amount) - amount
            summary.available_amount = quantize_amount(summary.available_amount) + amount
            summary.total_amount = quantize_amount(summary.total_amount)
            summary.updated_at = now()
            flow.status = CommissionStatus.SETTLED
            flow.settled_at = now()
            db.flush()
        if commit:
            db.commit()
        else:
            db.flush()

    @staticmethod
    def cancel_for_order(db: Session, order_id: int) -> None:
        order = db.query(Order).filter(Order.id == order_id).populate_existing().with_for_update().first()
        if not order:
            return
        CommissionService.assert_mode_isolation(db, order)
        flows = db.query(CommissionFlow).filter(
            CommissionFlow.order_id == order_id,
            CommissionFlow.status.in_([CommissionStatus.FROZEN, CommissionStatus.SETTLED]),
        ).order_by(CommissionFlow.id.asc()).populate_existing().with_for_update().all()
        for flow in flows:
            summary = db.query(UserCommission).filter(
                UserCommission.user_id == flow.beneficiary_user_id
            ).populate_existing().with_for_update().first()
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
        city_flows = db.query(CityPartnerCommissionFlow).filter(
            CityPartnerCommissionFlow.order_id == order_id,
            CityPartnerCommissionFlow.status.in_([CommissionStatus.FROZEN, CommissionStatus.SETTLED]),
        ).order_by(CityPartnerCommissionFlow.beneficiary_user_id.asc(), CityPartnerCommissionFlow.id.asc()).populate_existing().with_for_update().all()
        for flow in city_flows:
            if flow.beneficiary_user_id is None:
                flow.status = CommissionStatus.CANCELED
                continue
            summary = db.query(UserCommission).filter(UserCommission.user_id == flow.beneficiary_user_id).populate_existing().with_for_update().first()
            if not summary:
                flow.status = CommissionStatus.CANCELED
                continue
            amount = quantize_amount(flow.commission_amount)
            if flow.status == CommissionStatus.FROZEN:
                summary.frozen_amount = max(quantize_amount(summary.frozen_amount) - amount, Decimal('0.00'))
            else:
                available = quantize_amount(summary.available_amount)
                if available < amount:
                    raise ConflictError('Settled city partner commission balance is insufficient for refund')
                summary.available_amount = available - amount
            summary.total_amount = max(quantize_amount(summary.total_amount) - amount, Decimal('0.00'))
            summary.updated_at = now()
            flow.status = CommissionStatus.CANCELED
            db.flush()
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
        config = db.query(CommissionConfig).order_by(CommissionConfig.id.asc()).populate_existing().with_for_update().first()
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
        ).filter((ProductZoneConfig.city_partner_commission_enabled if CommissionService._current_mode(db) == CommissionMode.CITY_PARTNER else ProductZoneConfig.custom_commission_enabled).is_(True))
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
                CommissionService.serialize_product_rule(product, config_by_product_id[product.id], CommissionService._current_mode(db))
                for product in rows
            ],
            'total': total,
            'page': safe_page,
            'page_size': safe_page_size,
        }

    @staticmethod
    def serialize_product_rule(product: Product, config: ProductZoneConfig, mode=CommissionMode.ORIGINAL) -> dict:
        if mode == CommissionMode.CITY_PARTNER:
            return {'product_id': product.id, 'product_name': product.product_name, 'zone_type': product.zone_type.value,
                    'commission_mode': mode.value, 'method': 'FIXED_AMOUNT', 'updated_at': iso_datetime(config.updated_at),
                    **{key: float(value) if isinstance(value, Decimal) else value
                       for key, value in city_partner_rule_values(config).items()}}
        return {
            'commission_mode': CommissionMode.ORIGINAL.value,
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
        legacy = select(
            CommissionFlow.id, CommissionFlow.beneficiary_user_id, CommissionFlow.source_user_id,
            CommissionFlow.order_id, CommissionFlow.team_id, CommissionFlow.level, CommissionFlow.rate,
            CommissionFlow.base_amount, CommissionFlow.commission_amount, CommissionFlow.status,
            CommissionFlow.settled_at, CommissionFlow.created_at,
            literal('ORIGINAL').label('commission_mode'), literal(None).label('commission_role'),
            literal(None).label('calculated_amount'),
        )
        city = select(
            CityPartnerCommissionFlow.id, CityPartnerCommissionFlow.beneficiary_user_id,
            CityPartnerCommissionFlow.source_user_id, CityPartnerCommissionFlow.order_id, Order.team_id,
            CityPartnerCommissionFlow.level, literal(0), CityPartnerCommissionFlow.profit_pool_amount,
            CityPartnerCommissionFlow.commission_amount, CityPartnerCommissionFlow.status,
            CityPartnerCommissionFlow.settled_at, CityPartnerCommissionFlow.created_at,
            literal('CITY_PARTNER'), CityPartnerCommissionFlow.commission_role,
            case((CityPartnerCommissionFlow.calculation_precision_known.is_(True),
                  cast(CityPartnerCommissionFlow.calculated_amount, String)), else_=None),
        ).join(Order, Order.id == CityPartnerCommissionFlow.order_id)
        flows = legacy.union_all(city).subquery()
        beneficiary, source = aliased(User), aliased(User)
        query = db.query(flows, beneficiary.nickname.label('beneficiary_nickname'),
                         beneficiary.phone.label('beneficiary_phone'), source.nickname.label('source_nickname'),
                         source.phone.label('source_phone'), Order.order_no).outerjoin(
            beneficiary, beneficiary.id == flows.c.beneficiary_user_id,
        ).join(source, source.id == flows.c.source_user_id).join(Order, Order.id == flows.c.order_id)
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(flows.c.team_id == AdminScopeService.require_team_id(current_user))
        if keyword and keyword.strip():
            like_value = f'%{keyword.strip()}%'
            query = query.filter(or_(cast(flows.c.id, String).ilike(like_value), Order.order_no.ilike(like_value),
                                     beneficiary.nickname.ilike(like_value), beneficiary.phone.ilike(like_value),
                                     source.nickname.ilike(like_value), source.phone.ilike(like_value)))
        if status:
            query = query.filter(flows.c.status == status)
        total = query.count()
        rows = query.order_by(flows.c.created_at.desc(), flows.c.commission_mode, flows.c.id.desc()).offset(
            (safe_page - 1) * safe_page_size).limit(safe_page_size).all()
        items = []
        for row in rows:
            data = dict(row._mapping)
            if data.get('calculated_amount') is not None:
                raw = format(Decimal(str(data['calculated_amount'])), 'f')
                data['calculated_amount'] = raw.rstrip('0').rstrip('.') if '.' in raw else raw
            data['record_key'] = f"{data['commission_mode']}:{data['id']}"
            data['level_label'] = CommissionService.flow_role_label(data['commission_role'], data['level'])
            if data['beneficiary_user_id'] is None:
                data['beneficiary_nickname'] = '公司账户（历史流水）'
            for key in ('rate', 'base_amount', 'commission_amount'):
                data[key] = float(data[key] or 0)
            for key in ('created_at', 'settled_at'):
                data[key] = iso_datetime(data[key])
            data['status'] = str(data['status'])
            items.append(data)
        return {'items': items, 'total': total, 'page': safe_page, 'page_size': safe_page_size}

    @staticmethod
    def flow_role_label(role, level) -> str:
        return {'CITY_PARTNER': '城市合伙人', 'DIRECT': '直推奖', 'UPLINE': f'上级第{level}层',
                'COMPANY_REMAINDER': '公司尾差'}.get(role, '直属团队奖励' if level == TEAM_REWARD_FLOW_LEVEL else f'{level}级分润')

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
    def _commission_mode_status(db: Session) -> dict:
        config = db.query(CommissionConfig).order_by(CommissionConfig.id.asc()).first()
        mode = getattr(config, 'commission_mode', CommissionMode.ORIGINAL) if config else CommissionMode.ORIGINAL
        rule_version = getattr(config, 'commission_rule_version', 'legacy') if config else 'legacy'
        updated_at = getattr(config, 'updated_at', None) if config else None
        last_switch = db.query(CommissionModeSwitchLog).order_by(CommissionModeSwitchLog.id.desc()).first()
        operator = db.get(User, last_switch.operator_id) if last_switch and last_switch.operator_id else None
        pending_order_count = int(db.query(func.count(Order.id)).filter(
            Order.commission_mode == mode,
            Order.pay_status == PayStatus.PAID,
            Order.order_status.notin_([OrderStatus.COMPLETED, OrderStatus.REFUND]),
        ).scalar() or 0)
        old_frozen = db.query(func.coalesce(func.sum(CommissionFlow.commission_amount), 0)).filter(
            CommissionFlow.status == CommissionStatus.FROZEN,
        ).scalar() or 0
        city_frozen = db.query(func.coalesce(func.sum(CityPartnerCommissionFlow.commission_amount), 0)).filter(
            CityPartnerCommissionFlow.status == CommissionStatus.FROZEN,
        ).scalar() or 0
        return {
            'mode': mode,
            'rule_version': rule_version,
            'updated_by': getattr(config, 'updated_by', None) if config else None,
            'updated_at': iso_datetime(updated_at) if updated_at else None,
            'switched_at': iso_datetime(last_switch.switched_at) if last_switch else None,
            'operator_id': last_switch.operator_id if last_switch else None,
            'operator_name': operator.nickname if operator else None,
            'reason': last_switch.reason if last_switch else None,
            'pending_order_count': pending_order_count,
            'frozen_commission_amount': float(quantize_amount(Decimal(str(old_frozen)) + Decimal(str(city_frozen)))),
        }

    @staticmethod
    def commission_mode(db: Session) -> dict:
        return CommissionService._commission_mode_status(db)

    @staticmethod
    def mode_readiness(db: Session) -> dict:
        checks = []
        for account, label in [('COMPANY', '公司账户'), ('OPERATIONS', '运维账户')]:
            try:
                system_account(db, account)
                checks.append({'key': account, 'label': label, 'passed': True, 'message': '已配置'})
            except ConflictError as exc:
                checks.append({'key': account, 'label': label, 'passed': False, 'message': str(exc)})
        products = db.query(Product, ProductZoneConfig).join(
            ProductZoneConfig, ProductZoneConfig.product_id == Product.id,
        ).filter(ProductZoneConfig.city_partner_commission_enabled.is_(True)).all()
        errors = []
        for product, rules in products:
            try:
                validate_city_partner_rule(rules, product.sale_price, product.cost_price)
            except ConflictError as exc:
                errors.append(f'{product.product_name} (ID {product.id}): {exc}')
        checks.append({'key': 'products', 'label': '商品规则、成本与售价',
                       'passed': bool(products) and not errors,
                       'message': '; '.join(errors) if errors else (f'{len(products)} 个商品规则有效' if products else '至少启用一个商品的新模式规则')})
        seat_count = db.query(CityPartnerSeat).filter(CityPartnerSeat.status == 'ACTIVE').count()
        checks.append({'key': 'cities', 'label': '城市席位配置', 'passed': seat_count > 0,
                       'message': f'{seat_count} 个启用席位；允许尚无持有人' if seat_count else 'City configuration missing: 至少配置一个启用的城市席位'})
        policies = [
            '商品付款后冻结分润，订单完成即释放；当前不另设售后等待期。',
            '席位履约成功后禁止普通退款，已付款但未取得席位可退款；特殊退款尚不支持。',
            '按价格上限成交后停止轮换；同一用户可持有多个城市席位。',
            '无对应城市合伙人或上级时，未分配金额进入公司账户。',
            '原模式关闭移动端城市合伙人入口和新购；历史订单、分润与已发起支付的回调继续处理。',
        ]
        checks.append({'key': 'refund', 'label': '当前结算与退款规则', 'passed': True,
                       'message': '已采用下列规则；文档中的待定规则尚未变更'})
        return {'ready': all(item['passed'] for item in checks), 'checks': checks, 'policies': policies}

    @staticmethod
    def update_commission_mode(db: Session, mode: CommissionMode, operator_id: int, reason: str | None = None) -> dict:
        config = db.query(CommissionConfig).order_by(CommissionConfig.id.asc()).populate_existing().with_for_update().first()
        current_mode = getattr(config, 'commission_mode', CommissionMode.ORIGINAL) if config else CommissionMode.ORIGINAL
        if current_mode == mode:
            data = CommissionService._commission_mode_status(db)
            data['previous_mode'] = current_mode
            return data
        if mode == CommissionMode.CITY_PARTNER:
            readiness = CommissionService.mode_readiness(db)
            if not readiness['ready']:
                raise ConflictError('; '.join(item['message'] for item in readiness['checks'] if not item['passed']))
        before = CommissionService._commission_mode_status(db)
        switched_at = now()
        rule_version = f'{mode.value.lower()}-{uuid4().hex}'
        if not config:
            config = CommissionConfig(level1_rate=0, level2_rate=0, is_active=False, updated_at=switched_at)
            db.add(config)
            db.flush()
        config.commission_mode = mode
        config.commission_rule_version = rule_version
        config.updated_by = operator_id
        config.updated_at = switched_at
        db.add(CommissionModeSwitchLog(
            from_mode=current_mode, to_mode=mode, commission_rule_version=rule_version,
            switched_at=switched_at, operator_id=operator_id, reason=reason,
            pending_order_count=before['pending_order_count'],
            frozen_commission_amount=quantize_amount(before['frozen_commission_amount']), created_at=switched_at,
        ))
        db.commit()
        return {
            'mode': mode, 'previous_mode': current_mode, 'rule_version': rule_version,
            'switched_at': iso_datetime(switched_at), 'operator_id': operator_id, 'reason': reason,
            'pending_order_count': before['pending_order_count'],
            'frozen_commission_amount': before['frozen_commission_amount'],
        }

    @staticmethod
    def _current_mode(db: Session) -> CommissionMode:
        config = db.query(CommissionConfig).order_by(CommissionConfig.id.asc()).first()
        return getattr(config, 'commission_mode', CommissionMode.ORIGINAL) if config else CommissionMode.ORIGINAL

    @staticmethod
    def _floor_cent(value: Decimal) -> Decimal:
        return value.quantize(Decimal('0.01'), rounding='ROUND_DOWN')

    @staticmethod
    def settlement_failure(order: Order) -> str | None:
        snapshot = getattr(order, 'city_partner_rule_snapshot', None)
        return snapshot.get('settlement_error') if isinstance(snapshot, dict) else None

    @staticmethod
    def assert_mode_isolation(db: Session, order: Order) -> None:
        mode = getattr(order, 'commission_mode', None)
        tables = (CommissionFlow, RegionDividendFlow) if mode == CommissionMode.CITY_PARTNER else (CityPartnerCommissionFlow,)
        for table in tables:
            if db.query(table.id).filter(table.order_id == order.id).first():
                raise ConflictError('Order commission mode conflicts with existing flows; manual reconciliation required')

    @staticmethod
    def assert_fulfillable(order: Order) -> None:
        if CommissionService.settlement_failure(order):
            raise ConflictError('Paid order requires manual refund because commission settlement failed')

    @staticmethod
    def list_failed_settlements(db: Session, page=1, page_size=20) -> dict:
        query = db.query(Order).filter(
            Order.commission_mode == CommissionMode.CITY_PARTNER,
            Order.pay_status == PayStatus.PAID,
            Order.city_partner_rule_snapshot['settlement_error'].as_string().is_not(None),
        )
        total = query.count()
        rows = query.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {'total': total, 'items': [
            {'order_id': row.id, 'order_no': row.order_no, 'user_id': row.user_id,
             'paid_amount': str(row.paid_amount), 'paid_at': iso_datetime(row.paid_at),
             'settlement_error': CommissionService.settlement_failure(row),
             'rule_snapshot': row.city_partner_rule_snapshot,
             'sale_price_snapshot': str(row.sale_price_snapshot),
             'cost_price_snapshot': str(row.cost_price_snapshot),
             'profit_pool_snapshot': str(row.profit_pool_snapshot)} for row in rows
        ]}

    @staticmethod
    def _freeze_city_partner_rewards(db: Session, order: Order, buyer: User) -> None:
        if db.query(CityPartnerCommissionFlow.id).filter(CityPartnerCommissionFlow.order_id == order.id).first():
            return
        address_id = getattr(order, 'legacy_address_id', None)
        address = db.get(UserAddress, address_id) if address_id else None
        province, city = (getattr(address, 'province', '') or '', getattr(address, 'city', '') or '')
        seat = db.query(CityPartnerSeat).filter(
            CityPartnerSeat.province == province, CityPartnerSeat.city == city,
            CityPartnerSeat.status == 'ACTIVE', CityPartnerSeat.current_user_id.is_not(None),
        ).populate_existing().with_for_update().first() if province and city else None
        order.province, order.city = province or None, city or None
        order.city_partner_user_id = seat.current_user_id if seat else None
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).order_by(OrderItem.product_id.asc(), OrderItem.id.asc()).all()
        plans, snapshots, priced_items = [], [], []
        total_sale, total_cost = Decimal('0.00'), Decimal('0.00')
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).populate_existing().with_for_update(read=True).first()
            config = db.query(ProductZoneConfig).filter(ProductZoneConfig.product_id == item.product_id).populate_existing().with_for_update(read=True).first()
            quantity = int(item.quantity or 0)
            sale = quantize_amount(item.unit_price or 0)
            cost = quantize_amount(product.cost_price or 0) if product else Decimal('0.00')
            total_sale += sale * quantity
            total_cost += cost * quantity
            values = city_partner_rule_values(config)
            snapshots.append({'order_item_id': item.id, 'product_id': item.product_id,
                              'unit_sale': str(sale), 'unit_cost': str(cost),
                              'quantity': quantity, 'rule': {k: str(v) if isinstance(v, Decimal) else v for k, v in values.items()}})
            priced_items.append((item, product, config, quantity, sale, cost, values))

        order.city_partner_rule_snapshot = {
            'mode': 'CITY_PARTNER', 'version': order.commission_rule_version, 'items': snapshots,
            'ancestor_user_ids': [u.id for _, u in CommissionService._ancestor_users(db, buyer, 8)],
        }
        order.sale_price_snapshot = total_sale
        order.cost_price_snapshot = total_cost
        order.profit_pool_snapshot = max(Decimal('0.00'), total_sale - total_cost)
        try:
            CommissionService._allocate_city_partner_rewards(db, order, buyer, seat, priced_items, plans)
        except ConflictError as exc:
            # The caller rolls back the savepoint, including any partial credits,
            # then persists these inputs alongside the successful payment.
            snapshot = {key: getattr(order, key) for key in (
                'province', 'city', 'city_partner_user_id', 'sale_price_snapshot',
                'cost_price_snapshot', 'profit_pool_snapshot', 'city_partner_rule_snapshot',
            )}
            snapshot['city_partner_rule_snapshot'] = {
                **order.city_partner_rule_snapshot, 'settlement_error': exc.message,
            }
            raise CityPartnerSettlementError(exc.message, snapshot) from exc
        db.flush()

    @staticmethod
    def _allocate_city_partner_rewards(db, order, buyer, seat, priced_items, plans):
        for item, product, config, quantity, sale, cost, values in priced_items:
            if not product or not config or not config.city_partner_commission_enabled:
                continue
            validate_city_partner_rule(config, sale, product.cost_price)
            pool = (sale - cost) * quantity
            allocations = []
            city_amount = quantize_amount(values['city_partner_amount']) * quantity
            direct_amount = quantize_amount(values['city_partner_direct_reward_amount']) * quantity
            if seat and city_amount > 0:
                allocations.append((seat.current_user_id, 'CITY_PARTNER', None, city_amount, city_amount))
            ancestors = CommissionService._ancestor_users(db, buyer, 8)
            if ancestors and direct_amount > 0:
                allocations.append((ancestors[0][1].id, 'DIRECT', 0, direct_amount, direct_amount))
            amounts = upline_calculations(values, quantity)
            for level, (_, beneficiary) in enumerate(ancestors[1:], start=1):
                calculated, amount = amounts[level - 1]
                if amount > 0:
                    allocations.append((beneficiary.id, 'UPLINE', level, amount, calculated))
            allocated = sum((a[3] for a in allocations), Decimal('0.00'))
            remainder = quantize_amount(pool - allocated)
            if remainder < 0:
                raise ConflictError('City partner commission exceeds product profit pool')
            if remainder > 0:
                allocations.append((system_account(db, 'COMPANY').id, 'COMPANY_REMAINDER', None, remainder, remainder))
            for beneficiary_id, role, level, amount, calculated in allocations:
                plans.append((beneficiary_id, item, role, level, amount, pool, config, calculated))
        # All accounts touched by this order are locked in the same order, including repeated items.
        for beneficiary_id, item, role, level, amount, pool, config, calculated in sorted(plans, key=lambda p: p[0]):
            CommissionService._add_city_partner_flow(db, order, item, buyer, beneficiary_id, role, level, amount, pool, seat, config, calculated)

    @staticmethod
    def _add_city_partner_flow(db, order, item, buyer, beneficiary_id, role, level, amount, pool, seat, config, calculated):
        amount = quantize_amount(amount)
        if beneficiary_id and amount > 0:
            summary = db.query(UserCommission).filter(UserCommission.user_id == beneficiary_id).populate_existing().with_for_update().first()
            if not summary:
                summary = UserCommission(user_id=beneficiary_id, updated_at=now())
                db.add(summary)
                db.flush()
            summary.frozen_amount = quantize_amount(summary.frozen_amount) + amount
            summary.total_amount = quantize_amount(summary.total_amount) + amount
            summary.updated_at = now()
        db.add(CityPartnerCommissionFlow(
            order_id=order.id, order_item_id=item.id, product_id=item.product_id, order_no=order.order_no,
            commission_mode=CommissionMode.CITY_PARTNER,
            commission_rule_version=getattr(config, 'city_partner_commission_rule_version', 'v1'),
            province=order.province or '', city=order.city or '', city_partner_user_id=seat.current_user_id if seat else None,
            beneficiary_user_id=beneficiary_id, beneficiary_account='COMPANY' if role == 'COMPANY_REMAINDER' else None,
            source_user_id=buyer.id, commission_role=role, level=level,
            unit_sale_price=quantize_amount(item.unit_price or 0), unit_cost_price=quantize_amount((db.get(Product, item.product_id).cost_price if db.get(Product, item.product_id) else 0) or 0),
            quantity=int(item.quantity or 0), profit_pool_amount=quantize_amount(pool), calculated_amount=calculated,
            calculation_precision_known=True,
            commission_amount=quantize_amount(amount), remainder_amount=amount if role == 'COMPANY_REMAINDER' else Decimal('0.00'), status=CommissionStatus.FROZEN, created_at=now(),
        ))
        db.flush()

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
        locked_beneficiary_id = (
            db.query(User.id)
            .filter(User.id == beneficiary.id)
            .with_for_update()
            .scalar()
        )
        if locked_beneficiary_id is None:
            return
        commission = (
            db.query(UserCommission)
            .filter(UserCommission.user_id == beneficiary.id)
            .populate_existing()
            .with_for_update()
            .first()
        )
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
        # The next reward may refresh this same account (e.g. direct + team).
        # Persist its increment within this transaction before that refresh.
        db.flush()

    @staticmethod
    def _order_profit_items(db: Session, order_id: int) -> list[tuple[int, Decimal, Decimal]]:
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        if not items:
            return []
        product_ids = {item.product_id for item in items}
        products = {
            product.id: product
            for product in db.query(Product).filter(Product.id.in_(product_ids)).order_by(Product.id.asc()).populate_existing().with_for_update(read=True).all()
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
        ).order_by(ProductZoneConfig.product_id.asc()).populate_existing().with_for_update(read=True).all()
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
