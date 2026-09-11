from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CommissionRuleAudit(Base):
    __tablename__ = 'commission_rule_audits'
    __table_args__ = (Index('ix_commission_rule_audits_entity', 'entity_type', 'entity_id', 'id'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    before_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    after_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
