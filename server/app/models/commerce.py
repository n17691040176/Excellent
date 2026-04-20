from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserFavoriteProduct(Base):
    __tablename__ = 'user_favorite_products'
    __table_args__ = (UniqueConstraint('user_id', 'product_id', name='uk_user_favorite_products_user_product'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class UserProductFootprint(TimestampMixin, Base):
    __tablename__ = 'user_product_footprints'
    __table_args__ = (UniqueConstraint('user_id', 'product_id', name='uk_user_product_footprints_user_product'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False, index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_viewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class ShoppingCartItem(TimestampMixin, Base):
    __tablename__ = 'shopping_cart_items'
    __table_args__ = (UniqueConstraint('user_id', 'product_id', name='uk_shopping_cart_items_user_product'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False, index=True)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey('product_skus.id'), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
