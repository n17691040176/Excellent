from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.common import AppBaseModel


class CityPartnerSeatCreateRequest(AppBaseModel):
    change_reason: str | None = Field(default=None, max_length=500)
    province: str = Field(min_length=1, max_length=64)
    city: str = Field(min_length=1, max_length=64)
    initial_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    price_growth_rate: Decimal = Field(default=Decimal('20'), ge=0, le=100, max_digits=7, decimal_places=4)
    price_cap: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)

    @model_validator(mode='after')
    def validate_cap(self):
        from app.services.city_regions import city_regions
        self.province, self.city = self.province.strip(), self.city.strip()
        if self.city not in city_regions().get(self.province, []):
            raise ValueError('请选择与收货地址一致的标准省、市名称')
        if self.price_cap is not None and self.price_cap < self.initial_price:
            raise ValueError('price_cap must be greater than or equal to initial_price')
        return self


class CityPartnerSeatUpdateRequest(AppBaseModel):
    change_reason: str | None = Field(default=None, max_length=500)
    price_growth_rate: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=4)
    price_cap: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    status: str = Field(pattern='^(ACTIVE|INACTIVE)$')


class CityPartnerPurchaseRequest(AppBaseModel):
    order_id: int = Field(gt=0)


class CityPartnerSeatListQuery(AppBaseModel):
    province: str | None = None
    city: str | None = None


class CityPartnerOrderRequest(AppBaseModel):
    price_version: int = Field(ge=0)
