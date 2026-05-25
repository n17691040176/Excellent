from app.schemas.common import AppBaseModel


class EarningRuleCreateRequest(AppBaseModel):
    rule_code: str
    rule_name: str
    rule_type: str
    product_id: int | None = None
    member_level: str | None = None
    commission_level: int | None = None
    subject_type: str = 'USER'
    trigger_event: str
    calculation_basis: str
    calculation_method: str
    reward_rate: float = 0
    reward_amount: float = 0
    cap_amount: float | None = None
    min_condition: str | None = None
    qualification_level: str | None = None
    settlement_cycle: str = 'MONTHLY'
    settlement_delay_days: int = 0
    freeze_days: int = 0
    priority: int = 0
    is_active: bool = True
    compliance_note: str | None = None
    remark: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None


class EarningRuleUpdateRequest(AppBaseModel):
    rule_name: str
    rule_type: str
    product_id: int | None = None
    member_level: str | None = None
    commission_level: int | None = None
    subject_type: str = 'USER'
    trigger_event: str
    calculation_basis: str
    calculation_method: str
    reward_rate: float = 0
    reward_amount: float = 0
    cap_amount: float | None = None
    min_condition: str | None = None
    qualification_level: str | None = None
    settlement_cycle: str = 'MONTHLY'
    settlement_delay_days: int = 0
    freeze_days: int = 0
    priority: int = 0
    is_active: bool = True
    compliance_note: str | None = None
    remark: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None


class EarningRuleStatusRequest(AppBaseModel):
    is_active: bool
