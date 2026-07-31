from __future__ import annotations

from datetime import datetime
from decimal import Decimal

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
MEMBER_LEVEL_VALUES = {'NORMAL_MEMBER', 'DEALER', 'COUNTY_AGENT', 'CITY_AGENT'}

PB_OWNER_DAILY_RULE = 'PB_OWNER_DAILY'
PB_REFERRAL_DAILY_RULE = 'PB_REFERRAL_DAILY'


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
        if level not in {'DEALER', 'COUNTY_AGENT', 'CITY_AGENT'}:
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
