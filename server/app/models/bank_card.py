from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserBankCard(TimestampMixin, Base):
    __tablename__ = 'user_bank_cards'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    holder_name: Mapped[str] = mapped_column(String(64), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    card_number_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    card_last_four: Mapped[str] = mapped_column(String(4), nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

