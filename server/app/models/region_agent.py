"""区域代理模型 - 用户与省市区绑定关系"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegionAgent(Base):
    """区域代理绑定表 - 记录用户负责的区域"""
    __tablename__ = 'region_agents'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 用户信息
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # 代理区域 - 支持省、市、区三级
    province: Mapped[str] = mapped_column(String(64), nullable=False, default='')
    city: Mapped[str] = mapped_column(String(64), nullable=False, default='')
    district: Mapped[str] = mapped_column(String(64), nullable=False, default='')

    # 代理类型：区县代理、市代理
    agent_type: Mapped[str] = mapped_column(
        Enum('COUNTY_AGENT', 'CITY_AGENT', name='region_agent_type'),
        nullable=False,
        default='COUNTY_AGENT'
    )

    # 状态：PENDING待审核、APPROVED已通过、REJECTED已拒绝、EXPIRED已过期
    status: Mapped[str] = mapped_column(
        Enum('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', name='region_agent_status'),
        nullable=False,
        default='PENDING'
    )

    # 代理有效期
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 协议签署
    agreement_signed: Mapped[bool] = mapped_column(default=False)
    agreement_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 审核信息
    audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    audited_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 一手资源证明
    resource_proof_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 分红比例（可后台配置）
    dividend_rate: Mapped[float] = mapped_column(default=0.0)

    # 统计
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_dividend: Mapped[float] = mapped_column(default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    # 索引
    __table_args__ = (
        Index('idx_region_province', 'province'),
        Index('idx_region_city', 'city'),
        Index('idx_region_district', 'district'),
        Index('idx_region_agent_type', 'agent_type'),
        Index('idx_region_status', 'status'),
        # 同一用户同一区域只能有一条有效记录
        Index('idx_region_user_area', 'user_id', 'province', 'city', 'district', unique=True),
    )

    def is_valid(self) -> bool:
        """检查代理是否有效"""
        if self.status != 'APPROVED':
            return False
        if not self.agreement_signed:
            return False
        now = datetime.now()
        if self.effective_at and self.effective_at > now:
            return False
        return not (self.expired_at and self.expired_at < now)
