"""区域分红流水表"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegionDividendFlow(Base):
    """区域分红流水 - 记录每个订单的区域代理分红"""
    __tablename__ = 'region_dividend_flows'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 关联订单
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False)

    # 区域代理信息
    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    agent_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)  # COUNTY_AGENT / CITY_AGENT

    # 区域信息
    province: Mapped[str] = mapped_column(String(64), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    district: Mapped[str] = mapped_column(String(64), nullable=False)

    # 分红金额信息
    order_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)  # 订单实付金额
    dividend_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)  # 分红比例
    dividend_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)  # 分红金额

    # 状态：FROZEN冻结、SETTLED已结算、EXPIRED失效
    status: Mapped[str] = mapped_column(
        Enum('FROZEN', 'SETTLED', 'EXPIRED', name='dividend_flow_status'),
        nullable=False,
        default='FROZEN'
    )

    # 结算时间
    settled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 备注
    remark: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_dividend_agent', 'agent_user_id'),
        Index('idx_dividend_status', 'status'),
        Index('idx_dividend_created', 'created_at'),
    )
