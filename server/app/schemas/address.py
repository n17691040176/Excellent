from app.schemas.common import AppBaseModel


class AddressCreateRequest(AppBaseModel):
    receiver_name: str
    receiver_phone: str
    province: str
    city: str
    district: str
    detail_address: str
    is_default: bool = False


class AddressUpdateRequest(AppBaseModel):
    receiver_name: str | None = None
    receiver_phone: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    detail_address: str | None = None
    is_default: bool | None = None
