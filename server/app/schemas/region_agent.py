from datetime import datetime

from pydantic import Field

from app.schemas.common import AppBaseModel


class RegionAgentCreateRequest(AppBaseModel):
    user_id: int = Field(gt=0)
    agent_type: str
    province: str = Field(min_length=1, max_length=64)
    city: str = Field(min_length=1, max_length=64)
    district: str = Field(default='', max_length=64)
    dividend_rate: float | None = Field(default=None, ge=0, le=100)
    effective_at: datetime | None = None
    expired_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=500)


class RegionAgentUpdateRequest(AppBaseModel):
    agent_type: str
    province: str = Field(min_length=1, max_length=64)
    city: str = Field(min_length=1, max_length=64)
    district: str = Field(default='', max_length=64)
    dividend_rate: float = Field(ge=0, le=100)
    effective_at: datetime | None = None
    expired_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=500)
