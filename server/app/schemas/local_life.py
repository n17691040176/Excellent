from app.schemas.common import AppBaseModel


class LocalLifeOrderCreateRequest(AppBaseModel):
    service_id: int
    store_id: int | None = None
    quantity: int = 1
    points_amount: float = 0
    balance_amount: float = 0


class LocalLifeVerifyRequest(AppBaseModel):
    verification_code: str


class AdminLocalLifeMerchantCreateRequest(AppBaseModel):
    owner_user_id: int | None = None
    merchant_name: str
    category_name: str
    contact_phone: str
    city_code: str | None = None
    status: str = 'PENDING'


class AdminLocalLifeMerchantUpdateRequest(AppBaseModel):
    owner_user_id: int | None = None
    merchant_name: str
    category_name: str
    contact_phone: str
    city_code: str | None = None
    status: str = 'PENDING'


class AdminLocalLifeStoreCreateRequest(AppBaseModel):
    merchant_id: int
    store_name: str
    contact_phone: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    detail_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str = 'ACTIVE'


class AdminLocalLifeStoreUpdateRequest(AppBaseModel):
    merchant_id: int
    store_name: str
    contact_phone: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    detail_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str = 'ACTIVE'


class AdminLocalLifeServiceCreateRequest(AppBaseModel):
    merchant_id: int
    store_id: int | None = None
    service_name: str
    market_price: float | None = None
    sale_price: float
    service_type: str
    verification_type: str
    status: str = 'ON_SHELF'


class AdminLocalLifeServiceUpdateRequest(AppBaseModel):
    merchant_id: int
    store_id: int | None = None
    service_name: str
    market_price: float | None = None
    sale_price: float
    service_type: str
    verification_type: str
    status: str = 'ON_SHELF'


class AdminMerchantCommissionRuleCreateRequest(AppBaseModel):
    merchant_id: int | None = None
    county_agent_rate: float = 0
    city_agent_rate: float = 0
    user_rate: float = 0
    merchant_rate: float = 0
    device_rate: float = 0
    ad_rate: float = 0
    is_active: bool = True


class AdminMerchantCommissionRuleUpdateRequest(AppBaseModel):
    merchant_id: int | None = None
    county_agent_rate: float = 0
    city_agent_rate: float = 0
    user_rate: float = 0
    merchant_rate: float = 0
    device_rate: float = 0
    ad_rate: float = 0
    is_active: bool = True
