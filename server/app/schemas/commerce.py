from pydantic import Field

from app.schemas.common import AppBaseModel


class CartItemCreateRequest(AppBaseModel):
    product_id: int
    quantity: int = 1


class CartItemUpdateRequest(AppBaseModel):
    quantity: int | None = None
    selected: bool | None = None


class CartCheckoutRequest(AppBaseModel):
    item_ids: list[int] = Field(default_factory=list)
    address_id: int | None = None
    points_amount: float = 0
    pay_channel: str = 'BALANCE'
    auto_complete: bool = True
