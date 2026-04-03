from app.schemas.common import AppBaseModel


class WithdrawCreateRequest(AppBaseModel):
    withdraw_type: str
    amount: float
    remark: str | None = None
