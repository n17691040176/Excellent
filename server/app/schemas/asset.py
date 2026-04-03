from app.schemas.common import AppBaseModel


class AssetTransferRequest(AppBaseModel):
    to_user_id: int
    amount: float
    remark: str | None = None
