from sqlalchemy import JSON, BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PageDecoration(TimestampMixin, Base):
    __tablename__ = 'page_decorations'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    page_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey('teams.id'), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
