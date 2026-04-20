from app.schemas.common import AppBaseModel


class AssetTransferRequest(AppBaseModel):
    to_user_id: int
    amount: float
    remark: str | None = None


class AdminPowerBankCreateRequest(AppBaseModel):
    device_code: str
    device_name: str | None = None
    remark: str | None = None


class AdminPowerBankUpdateRequest(AppBaseModel):
    status: str
