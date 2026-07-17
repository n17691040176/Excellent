from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.earning_rule import EarningRule
from app.models.user import User
from app.schemas.earning_rule import EarningRuleCreateRequest, EarningRuleUpdateRequest
from app.utils.helpers import quantize_amount

RULE_TYPE_VALUES = {
    'MEMBER_LEVEL',
    'DIRECT_REWARD',
    'DEVICE_INCOME',
    'TEAM_REWARD',
    'POOL_DISTRIBUTION',
    'SUBSIDY',
    'OFFLINE_BENEFIT',
}
SUBJECT_TYPE_VALUES = {'USER', 'TEAM', 'ORDER', 'DEVICE', 'POOL', 'PROJECT'}
CALCULATION_METHOD_VALUES = {'FIXED_AMOUNT', 'RATE', 'TIERED_RATE', 'WEIGHTED_POOL', 'MANUAL_AUDIT'}
SETTLEMENT_CYCLE_VALUES = {'IMMEDIATE', 'DAILY', 'WEEKLY', 'HALF_MONTHLY', 'MONTHLY', 'YEARLY', 'MANUAL'}
MEMBER_LEVEL_VALUES = {'NORMAL_MEMBER', 'VIP_MEMBER', 'DEALER', 'MASTER_DEALER'}

PB_OWNER_DAILY_RULE = 'PB_OWNER_DAILY'
PB_REFERRAL_DAILY_RULE = 'PB_REFERRAL_DAILY'

DEFAULT_EARNING_RULES: list[dict[str, Any]] = [
    {
        'rule_code': PB_OWNER_DAILY_RULE,
        'rule_name': '充电宝机主日收益',
        'rule_type': 'DEVICE_INCOME',
        'subject_type': 'DEVICE',
        'trigger_event': 'DAILY_SETTLEMENT',
        'calculation_basis': '托管充电宝单台有效设备',
        'calculation_method': 'FIXED_AMOUNT',
        'reward_amount': Decimal('0.75'),
        'settlement_cycle': 'DAILY',
        'is_active': True,
        'compliance_note': '基于真实设备和有效运营天数结算，需保留设备编号和日收益流水。',
    },
    {
        'rule_code': PB_REFERRAL_DAILY_RULE,
        'rule_name': '充电宝推荐日收益',
        'rule_type': 'DIRECT_REWARD',
        'subject_type': 'DEVICE',
        'trigger_event': 'DAILY_SETTLEMENT',
        'calculation_basis': '直推用户托管充电宝单台有效设备',
        'calculation_method': 'FIXED_AMOUNT',
        'reward_amount': Decimal('0.25'),
        'settlement_cycle': 'DAILY',
        'is_active': True,
        'compliance_note': '仅限直接推荐关系，基于真实设备收益，不扩展多层级。',
    },
    {
        'rule_code': 'MEMBER_NORMAL_ACTIVATE',
        'rule_name': '普通会员分销激活',
        'rule_type': 'MEMBER_LEVEL',
        'member_level': 'NORMAL_MEMBER',
        'subject_type': 'USER',
        'trigger_event': 'PAID_ORDER_EXISTS',
        'calculation_basis': '任意真实商品订单已支付',
        'calculation_method': 'MANUAL_AUDIT',
        'settlement_cycle': 'MANUAL',
        'is_active': True,
        'compliance_note': '免费注册，购买任意商品后才具备分销收益资格，不允许购买点位。',
    },
    {
        'rule_code': 'MEMBER_VIP_ACTIVATE',
        'rule_name': 'VIP会员激活',
        'rule_type': 'MEMBER_LEVEL',
        'member_level': 'VIP_MEMBER',
        'subject_type': 'USER',
        'trigger_event': 'CONSUMPTION_OR_GIFT_PACKAGE',
        'calculation_basis': '消费达标或自愿购买等值实物会员礼包',
        'calculation_method': 'MANUAL_AUDIT',
        'settlement_cycle': 'MANUAL',
        'is_active': True,
        'compliance_note': '会员礼包必须为等值实物产品，禁止纯充值、虚拟权益付费。',
    },
    {
        'rule_code': 'MEMBER_DEALER_UPGRADE',
        'rule_name': '经销商晋升',
        'rule_type': 'MEMBER_LEVEL',
        'member_level': 'DEALER',
        'subject_type': 'USER',
        'trigger_event': 'MONTHLY_PERFORMANCE_AUDIT',
        'calculation_basis': '个人销售额 + 直接推荐团队月销售额',
        'calculation_method': 'MANUAL_AUDIT',
        'settlement_cycle': 'MONTHLY',
        'is_active': True,
        'compliance_note': '仅按真实销售业绩晋升，严禁花钱购买等级。',
    },
    {
        'rule_code': 'MEMBER_MASTER_DEALER_UPGRADE',
        'rule_name': '总经销商晋升',
        'rule_type': 'MEMBER_LEVEL',
        'member_level': 'MASTER_DEALER',
        'subject_type': 'TEAM',
        'trigger_event': 'MONTHLY_PERFORMANCE_AUDIT',
        'calculation_basis': '团队整体月销售额',
        'calculation_method': 'MANUAL_AUDIT',
        'settlement_cycle': 'MONTHLY',
        'is_active': True,
        'compliance_note': '只作为奖励比例划分依据，不设置层级管控或人头绑定。',
    },
    {
        'rule_code': 'DISTRIBUTION_LEVEL_1',
        'rule_name': '一级分销佣金',
        'rule_type': 'DIRECT_REWARD',
        'subject_type': 'ORDER',
        'trigger_event': 'ORDER_COMPLETE',
        'calculation_basis': '商品利润',
        'calculation_method': 'RATE',
        'commission_level': 1,
        'reward_rate': Decimal('15.0000'),
        'settlement_cycle': 'IMMEDIATE',
        'is_active': True,
        'compliance_note': 'A推荐B，B真实下单后，订单确认完成且无售后纠纷后结算。',
    },
    {
        'rule_code': 'DISTRIBUTION_LEVEL_2',
        'rule_name': '二级分销佣金',
        'rule_type': 'DIRECT_REWARD',
        'subject_type': 'ORDER',
        'trigger_event': 'ORDER_COMPLETE',
        'calculation_basis': '商品利润',
        'calculation_method': 'RATE',
        'commission_level': 2,
        'reward_rate': Decimal('5.0000'),
        'settlement_cycle': 'IMMEDIATE',
        'is_active': True,
        'compliance_note': 'A-B-C关系中，C真实下单后A获得二级佣金。',
    },
    {
        'rule_code': 'DISTRIBUTION_LEVEL_3',
        'rule_name': '三级分销佣金',
        'rule_type': 'DIRECT_REWARD',
        'subject_type': 'ORDER',
        'trigger_event': 'ORDER_COMPLETE',
        'calculation_basis': '商品利润',
        'calculation_method': 'RATE',
        'commission_level': 3,
        'reward_rate': Decimal('3.0000'),
        'settlement_cycle': 'IMMEDIATE',
        'is_active': True,
        'compliance_note': '系统强制最多三级，四级及以上不结算佣金。',
    },
    {
        'rule_code': 'TEAM_REWARD_VIP',
        'rule_name': 'VIP团队销售奖',
        'rule_type': 'TEAM_REWARD',
        'member_level': 'VIP_MEMBER',
        'subject_type': 'TEAM',
        'trigger_event': 'ORDER_COMPLETE',
        'calculation_basis': '直接推荐团队商品利润',
        'calculation_method': 'RATE',
        'reward_rate': Decimal('2.0000'),
        'settlement_cycle': 'IMMEDIATE',
        'is_active': True,
        'compliance_note': '只计算本人直接推荐的下级团队销售，不跨代、不无限穿透。',
    },
    {
        'rule_code': 'TEAM_REWARD_DEALER',
        'rule_name': '经销商团队销售奖',
        'rule_type': 'TEAM_REWARD',
        'member_level': 'DEALER',
        'subject_type': 'TEAM',
        'trigger_event': 'ORDER_COMPLETE',
        'calculation_basis': '直接推荐团队商品利润',
        'calculation_method': 'RATE',
        'reward_rate': Decimal('4.0000'),
        'settlement_cycle': 'IMMEDIATE',
        'is_active': True,
        'compliance_note': '只计算本人直接推荐的下级团队销售，不跨代、不无限穿透。',
    },
    {
        'rule_code': 'TEAM_REWARD_MASTER_DEALER',
        'rule_name': '总经销商团队销售奖',
        'rule_type': 'TEAM_REWARD',
        'member_level': 'MASTER_DEALER',
        'subject_type': 'TEAM',
        'trigger_event': 'ORDER_COMPLETE',
        'calculation_basis': '直接推荐团队商品利润',
        'calculation_method': 'RATE',
        'reward_rate': Decimal('6.0000'),
        'settlement_cycle': 'IMMEDIATE',
        'is_active': True,
        'compliance_note': '只计算本人直接推荐的下级团队销售，不跨代、不无限穿透。',
    },
    {
        'rule_code': 'RETAIL_REPURCHASE_REWARD',
        'rule_name': '零售复购奖',
        'rule_type': 'DIRECT_REWARD',
        'subject_type': 'ORDER',
        'trigger_event': 'REPEAT_PURCHASE',
        'calculation_basis': '复购订单商品利润',
        'calculation_method': 'RATE',
        'commission_level': 1,
        'reward_rate': Decimal('2.0000'),
        'settlement_cycle': 'IMMEDIATE',
        'is_active': True,
        'compliance_note': '仅基于真实复购订单的小额奖励，不与发展会员数量直接关联。',
    },
    {
        'rule_code': 'DIRECT_OPERATOR_REWARD',
        'rule_name': '运营商直推奖励',
        'rule_type': 'DIRECT_REWARD',
        'subject_type': 'ORDER',
        'trigger_event': 'ORDER_COMPLETE',
        'calculation_basis': '运营商服务包实付金额',
        'calculation_method': 'RATE',
        'reward_rate': Decimal('10.0000'),
        'settlement_cycle': 'IMMEDIATE',
        'settlement_delay_days': 1,
        'freeze_days': 0,
        'is_active': False,
        'compliance_note': '上线前需确认奖励基于真实销售服务，不以发展人员资格或层级人数为计酬依据。',
    },
    {
        'rule_code': 'SERVICE_FEE_SHARE',
        'rule_name': '服务费分润',
        'rule_type': 'DIRECT_REWARD',
        'subject_type': 'ORDER',
        'trigger_event': 'SERVICE_FEE_PAID',
        'calculation_basis': '年度服务费实收金额',
        'calculation_method': 'RATE',
        'reward_rate': Decimal('5.0000'),
        'settlement_cycle': 'MONTHLY',
        'is_active': False,
        'compliance_note': '仅按实际服务费收入核算，需支持退款冲正。',
    },
    {
        'rule_code': 'TEAM_SUPERVISOR_REWARD',
        'rule_name': '主管团队绩效奖',
        'rule_type': 'TEAM_REWARD',
        'subject_type': 'TEAM',
        'trigger_event': 'MONTH_END',
        'calculation_basis': '团队确认业绩',
        'calculation_method': 'RATE',
        'reward_rate': Decimal('5.0000'),
        'min_condition': '团队总业绩达到100000，指定业务达到30000',
        'qualification_level': 'SUPERVISOR',
        'settlement_cycle': 'MONTHLY',
        'is_active': False,
        'compliance_note': '需以真实订单确认业绩为准，并设置退款、撤销、封顶和审计流程。',
    },
    {
        'rule_code': 'TEAM_MANAGER_REWARD',
        'rule_name': '经理团队绩效奖',
        'rule_type': 'TEAM_REWARD',
        'subject_type': 'TEAM',
        'trigger_event': 'MONTH_END',
        'calculation_basis': '团队确认业绩',
        'calculation_method': 'RATE',
        'reward_rate': Decimal('8.0000'),
        'min_condition': '团队总业绩达到600000，指定业务达到100000',
        'qualification_level': 'MANAGER',
        'settlement_cycle': 'MONTHLY',
        'is_active': False,
        'compliance_note': '上线前需限定团队层级和计酬边界，避免无限层级团队计酬。',
    },
    {
        'rule_code': 'TEAM_DIRECTOR_REWARD',
        'rule_name': '总监团队绩效奖',
        'rule_type': 'TEAM_REWARD',
        'subject_type': 'TEAM',
        'trigger_event': 'MONTH_END',
        'calculation_basis': '团队确认业绩',
        'calculation_method': 'RATE',
        'reward_rate': Decimal('10.0000'),
        'min_condition': '团队总业绩达到1500000，指定业务达到500000',
        'qualification_level': 'DIRECTOR',
        'settlement_cycle': 'MONTHLY',
        'is_active': False,
        'compliance_note': '需设置收益封顶、平级奖限制和人工复核。',
    },
    {
        'rule_code': 'AD_POOL_DISTRIBUTION',
        'rule_name': '广告净收益池分配',
        'rule_type': 'POOL_DISTRIBUTION',
        'subject_type': 'POOL',
        'trigger_event': 'MONTH_END',
        'calculation_basis': '广告业务月度净收益',
        'calculation_method': 'WEIGHTED_POOL',
        'reward_rate': Decimal('10.0000'),
        'settlement_cycle': 'MONTHLY',
        'is_active': False,
        'compliance_note': '按实际净收益和权重快照分配，不承诺固定收益。',
    },
    {
        'rule_code': 'MALL_POOL_DISTRIBUTION',
        'rule_name': '商城净收益池分配',
        'rule_type': 'POOL_DISTRIBUTION',
        'subject_type': 'POOL',
        'trigger_event': 'MONTH_END',
        'calculation_basis': '商城业务月度净收益',
        'calculation_method': 'WEIGHTED_POOL',
        'reward_rate': Decimal('10.0000'),
        'settlement_cycle': 'MONTHLY',
        'is_active': False,
        'compliance_note': '需先扣除成本、退款、税费和售后风险金，再按权重分配。',
    },
    {
        'rule_code': 'STUDIO_LANDING_SUBSIDY',
        'rule_name': '工作室落地补贴',
        'rule_type': 'SUBSIDY',
        'subject_type': 'PROJECT',
        'trigger_event': 'MANUAL_AUDIT',
        'calculation_basis': '工作室落地验收',
        'calculation_method': 'FIXED_AMOUNT',
        'reward_amount': Decimal('500.00'),
        'settlement_cycle': 'MANUAL',
        'is_active': False,
        'compliance_note': '按落地验收材料人工审核，分期发放需生成补贴批次。',
    },
    {
        'rule_code': 'PERFORMANCE_1M_SUBSIDY',
        'rule_name': '团队百万业绩补贴',
        'rule_type': 'SUBSIDY',
        'subject_type': 'TEAM',
        'trigger_event': 'MANUAL_AUDIT',
        'calculation_basis': '团队确认业绩达100万',
        'calculation_method': 'FIXED_AMOUNT',
        'reward_amount': Decimal('30000.00'),
        'settlement_cycle': 'MANUAL',
        'is_active': False,
        'compliance_note': '需后台审核业绩口径、退款扣减和补贴预算。',
    },
    {
        'rule_code': 'OFFLINE_EQUITY_INTENT',
        'rule_name': '线下股权权益记录',
        'rule_type': 'OFFLINE_BENEFIT',
        'subject_type': 'USER',
        'trigger_event': 'MANUAL_AUDIT',
        'calculation_basis': '线下协议和工商/证券合规文件',
        'calculation_method': 'MANUAL_AUDIT',
        'reward_amount': Decimal('0.00'),
        'settlement_cycle': 'MANUAL',
        'is_active': False,
        'compliance_note': '股权事项不得作为钱包余额或可提现收益入账，只记录线下协议状态。',
    },
]


class EarningRuleService:
    @staticmethod
    def serialize(rule: EarningRule) -> dict:
        return {
            'id': rule.id,
            'rule_code': rule.rule_code,
            'rule_name': rule.rule_name,
            'rule_type': rule.rule_type,
            'product_id': rule.product_id,
            'member_level': rule.member_level,
            'commission_level': rule.commission_level,
            'subject_type': rule.subject_type,
            'trigger_event': rule.trigger_event,
            'calculation_basis': rule.calculation_basis,
            'calculation_method': rule.calculation_method,
            'reward_rate': float(rule.reward_rate or 0),
            'reward_amount': float(rule.reward_amount or 0),
            'cap_amount': float(rule.cap_amount) if rule.cap_amount is not None else None,
            'min_condition': rule.min_condition,
            'qualification_level': rule.qualification_level,
            'settlement_cycle': rule.settlement_cycle,
            'settlement_delay_days': rule.settlement_delay_days,
            'freeze_days': rule.freeze_days,
            'priority': rule.priority,
            'is_active': rule.is_active,
            'compliance_note': rule.compliance_note,
            'remark': rule.remark,
            'valid_from': rule.valid_from.isoformat() if rule.valid_from else None,
            'valid_to': rule.valid_to.isoformat() if rule.valid_to else None,
            'created_by': rule.created_by,
            'updated_by': rule.updated_by,
            'created_at': rule.created_at.isoformat() if rule.created_at else None,
            'updated_at': rule.updated_at.isoformat() if rule.updated_at else None,
        }

    @staticmethod
    def ensure_default_rules(db: Session) -> None:
        existed_codes = {code for (code,) in db.query(EarningRule.rule_code).all()}
        changed = False
        for data in DEFAULT_EARNING_RULES:
            if data['rule_code'] in existed_codes:
                continue
            db.add(EarningRule(**EarningRuleService._normalize_data(data)))
            changed = True
        if changed:
            db.commit()

    @staticmethod
    def list_rules(db: Session, rule_type: str | None = None, is_active: bool | None = None) -> list[dict]:
        query = db.query(EarningRule)
        if rule_type:
            query = query.filter(EarningRule.rule_type == rule_type)
        if is_active is not None:
            query = query.filter(EarningRule.is_active.is_(is_active))
        rows = query.order_by(EarningRule.priority.desc(), EarningRule.id.asc()).all()
        return [EarningRuleService.serialize(row) for row in rows]

    @staticmethod
    def get_rule(db: Session, rule_id: int) -> EarningRule:
        rule = db.get(EarningRule, rule_id)
        if not rule:
            raise NotFoundError('Earning rule not found')
        return rule

    @staticmethod
    def get_active_rule_by_code(db: Session, rule_code: str) -> EarningRule | None:
        return db.query(EarningRule).filter(
            EarningRule.rule_code == rule_code,
            EarningRule.is_active.is_(True),
        ).first()

    @staticmethod
    def fixed_amount(db: Session, rule_code: str, fallback: Decimal) -> Decimal:
        rule = EarningRuleService.get_active_rule_by_code(db, rule_code)
        if not rule:
            return quantize_amount(fallback)
        return quantize_amount(rule.reward_amount or fallback)

    @staticmethod
    def rate_for_commission_level(
        db: Session,
        level: int,
        product_id: int | None = None,
        trigger_event: str = 'ORDER_COMPLETE',
    ) -> Decimal:
        if level < 1 or level > 3:
            return Decimal('0')
        query = EarningRuleService._active_rate_query(db).filter(
            EarningRule.rule_type == 'DIRECT_REWARD',
            EarningRule.commission_level == level,
            EarningRule.trigger_event == str(trigger_event or '').strip().upper(),
        )
        if product_id:
            product_rule = query.filter(EarningRule.product_id == product_id).order_by(
                EarningRule.priority.desc(),
                EarningRule.id.desc(),
            ).first()
            if product_rule:
                return EarningRuleService._rate_decimal(product_rule.reward_rate)
        generic_rule = query.filter(EarningRule.product_id.is_(None)).order_by(
            EarningRule.priority.desc(),
            EarningRule.id.desc(),
        ).first()
        return EarningRuleService._rate_decimal(generic_rule.reward_rate) if generic_rule else Decimal('0')

    @staticmethod
    def rate_for_team_member_level(db: Session, member_level: str | None) -> Decimal:
        level = str(member_level or '').strip().upper()
        if level not in {'VIP_MEMBER', 'DEALER', 'MASTER_DEALER'}:
            return Decimal('0')
        rule = EarningRuleService._active_rate_query(db).filter(
            EarningRule.rule_type == 'TEAM_REWARD',
            EarningRule.member_level == level,
        ).order_by(
            EarningRule.priority.desc(),
            EarningRule.id.desc(),
        ).first()
        return EarningRuleService._rate_decimal(rule.reward_rate) if rule else Decimal('0')

    @staticmethod
    def create_rule(db: Session, current_user: User, payload: EarningRuleCreateRequest) -> dict:
        rule_code = EarningRuleService._clean_code(payload.rule_code)
        existed = db.query(EarningRule).filter(EarningRule.rule_code == rule_code).first()
        if existed:
            raise ConflictError('Rule code already exists')
        data = EarningRuleService._payload_to_data(payload, include_code=True)
        data['rule_code'] = rule_code
        data['created_by'] = current_user.id
        data['updated_by'] = current_user.id
        rule = EarningRule(**data)
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return EarningRuleService.serialize(rule)

    @staticmethod
    def update_rule(db: Session, rule_id: int, current_user: User, payload: EarningRuleUpdateRequest) -> dict:
        rule = EarningRuleService.get_rule(db, rule_id)
        data = EarningRuleService._payload_to_data(payload, include_code=False)
        for key, value in data.items():
            setattr(rule, key, value)
        rule.updated_by = current_user.id
        db.commit()
        db.refresh(rule)
        return EarningRuleService.serialize(rule)

    @staticmethod
    def update_status(db: Session, rule_id: int, current_user: User, is_active: bool) -> dict:
        rule = EarningRuleService.get_rule(db, rule_id)
        rule.is_active = is_active
        rule.updated_by = current_user.id
        db.commit()
        db.refresh(rule)
        return EarningRuleService.serialize(rule)

    @staticmethod
    def delete_rule(db: Session, rule_id: int) -> None:
        rule = EarningRuleService.get_rule(db, rule_id)
        db.delete(rule)
        db.commit()

    @staticmethod
    def _payload_to_data(payload: EarningRuleCreateRequest | EarningRuleUpdateRequest, include_code: bool) -> dict:
        data = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        if not include_code:
            data.pop('rule_code', None)
        return EarningRuleService._normalize_data(data)

    @staticmethod
    def _normalize_data(data: dict) -> dict:
        normalized = dict(data)
        normalized['rule_name'] = EarningRuleService._clean_required(normalized.get('rule_name'), 'Rule name is required')
        normalized['rule_type'] = EarningRuleService._clean_choice(normalized.get('rule_type'), RULE_TYPE_VALUES, 'Rule type invalid')
        normalized['subject_type'] = EarningRuleService._clean_choice(normalized.get('subject_type') or 'USER', SUBJECT_TYPE_VALUES, 'Subject type invalid')
        normalized['trigger_event'] = EarningRuleService._clean_required(normalized.get('trigger_event'), 'Trigger event is required')
        normalized['calculation_basis'] = EarningRuleService._clean_required(normalized.get('calculation_basis'), 'Calculation basis is required')
        normalized['calculation_method'] = EarningRuleService._clean_choice(
            normalized.get('calculation_method'),
            CALCULATION_METHOD_VALUES,
            'Calculation method invalid',
        )
        normalized['settlement_cycle'] = EarningRuleService._clean_choice(
            normalized.get('settlement_cycle') or 'MONTHLY',
            SETTLEMENT_CYCLE_VALUES,
            'Settlement cycle invalid',
        )
        normalized['product_id'] = EarningRuleService._optional_positive_int(normalized.get('product_id'), 'Product id invalid')
        normalized['member_level'] = EarningRuleService._clean_optional_choice(
            normalized.get('member_level'),
            MEMBER_LEVEL_VALUES,
            'Member level invalid',
        )
        normalized['commission_level'] = EarningRuleService._optional_int_range(
            normalized.get('commission_level'),
            1,
            3,
            'Commission level must be between 1 and 3',
        )
        normalized['reward_rate'] = EarningRuleService._safe_decimal(normalized.get('reward_rate'), max_value=Decimal('100.0000'))
        normalized['reward_amount'] = EarningRuleService._safe_decimal(normalized.get('reward_amount'))
        normalized['cap_amount'] = (
            None
            if normalized.get('cap_amount') in {None, ''}
            else EarningRuleService._safe_decimal(normalized.get('cap_amount'))
        )
        normalized['settlement_delay_days'] = EarningRuleService._safe_int(normalized.get('settlement_delay_days'), 0, 365)
        normalized['freeze_days'] = EarningRuleService._safe_int(normalized.get('freeze_days'), 0, 365)
        normalized['priority'] = EarningRuleService._safe_int(normalized.get('priority'), -10000, 10000)
        normalized['is_active'] = bool(normalized.get('is_active'))
        normalized['valid_from'] = EarningRuleService._parse_datetime(normalized.get('valid_from'))
        normalized['valid_to'] = EarningRuleService._parse_datetime(normalized.get('valid_to'))
        for key in {'min_condition', 'qualification_level', 'compliance_note', 'remark'}:
            normalized[key] = EarningRuleService._clean_optional(normalized.get(key))
        if normalized['valid_from'] and normalized['valid_to'] and normalized['valid_from'] > normalized['valid_to']:
            raise ConflictError('Valid from must be before valid to')
        return normalized

    @staticmethod
    def _active_rate_query(db: Session):
        current = datetime.now()
        return db.query(EarningRule).filter(
            EarningRule.is_active.is_(True),
            EarningRule.calculation_method == 'RATE',
            EarningRule.reward_rate > 0,
            (EarningRule.valid_from.is_(None) | (EarningRule.valid_from <= current)),
            (EarningRule.valid_to.is_(None) | (EarningRule.valid_to >= current)),
        )

    @staticmethod
    def _rate_decimal(value: object) -> Decimal:
        return Decimal(str(value or '0')) / Decimal('100')

    @staticmethod
    def _clean_code(value: str | None) -> str:
        code = str(value or '').strip().upper()
        if not code:
            raise ConflictError('Rule code is required')
        if any(char for char in code if not (char.isalnum() or char == '_')):
            raise ConflictError('Rule code only supports letters, numbers and underscore')
        return code

    @staticmethod
    def _clean_required(value: object, message: str) -> str:
        text = str(value or '').strip()
        if not text:
            raise ConflictError(message)
        return text

    @staticmethod
    def _clean_optional(value: object) -> str | None:
        text = str(value or '').strip()
        return text or None

    @staticmethod
    def _clean_choice(value: object, choices: set[str], message: str) -> str:
        text = str(value or '').strip().upper()
        if text not in choices:
            raise ConflictError(message)
        return text

    @staticmethod
    def _clean_optional_choice(value: object, choices: set[str], message: str) -> str | None:
        text = str(value or '').strip().upper()
        if not text:
            return None
        if text not in choices:
            raise ConflictError(message)
        return text

    @staticmethod
    def _optional_positive_int(value: object, message: str) -> int | None:
        if value in {None, ''}:
            return None
        number = EarningRuleService._to_int(value)
        if number <= 0:
            raise ConflictError(message)
        return number

    @staticmethod
    def _optional_int_range(value: object, min_value: int, max_value: int, message: str) -> int | None:
        if value in {None, ''}:
            return None
        number = EarningRuleService._to_int(value)
        if number < min_value or number > max_value:
            raise ConflictError(message)
        return number

    @staticmethod
    def _safe_decimal(value: object, max_value: Decimal | None = None) -> Decimal:
        amount = Decimal(str(value or '0'))
        if amount < 0:
            raise ConflictError('Amount or rate cannot be negative')
        if max_value is not None and amount > max_value:
            raise ConflictError('Rate cannot exceed 100')
        return amount

    @staticmethod
    def _safe_int(value: object, min_value: int, max_value: int) -> int:
        number = EarningRuleService._to_int(value or 0)
        if number < min_value or number > max_value:
            raise ConflictError(f'Integer field must be between {min_value} and {max_value}')
        return number

    @staticmethod
    def _to_int(value: object) -> int:
        if isinstance(value, int | float | Decimal):
            return int(value)
        return int(str(value))

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError as exc:
            raise ConflictError('Datetime format invalid') from exc
