from typing import Literal

from pydantic import Field

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
