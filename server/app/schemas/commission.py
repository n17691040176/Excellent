from typing import Literal

from pydantic import Field

from app.models.enums import CommissionMode
from app.schemas.common import AppBaseModel


class WithdrawCreateRequest(AppBaseModel):
    withdraw_type: Literal['COMMISSION'] = 'COMMISSION'
    amount: float = Field(gt=0)
    bank_card_id: int = Field(gt=0)
    remark: str | None = Field(default=None, max_length=500)


class WithdrawReviewRequest(AppBaseModel):
    remark: str | None = Field(default=None, max_length=500)


class WithdrawRejectRequest(AppBaseModel):
    remark: str = Field(min_length=1, max_length=500)


class WithdrawConfigUpdateRequest(AppBaseModel):
    fee_rate: float = Field(ge=0, le=100)
    min_amount: float = Field(gt=0)
    max_amount: float = Field(gt=0)


class CommissionModeUpdateRequest(AppBaseModel):
    mode: CommissionMode
    reason: str | None = Field(default=None, max_length=500)


class CommissionModeResponse(AppBaseModel):
    mode: CommissionMode
    rule_version: str
    updated_by: int | None = None
    updated_at: str | None = None
    pending_order_count: int = 0
    frozen_commission_amount: float = 0


class CommissionModeSwitchResponse(AppBaseModel):
    mode: CommissionMode
    previous_mode: CommissionMode
    rule_version: str
    switched_at: str
    operator_id: int
    reason: str | None = None
    pending_order_count: int = 0
    frozen_commission_amount: float = 0
