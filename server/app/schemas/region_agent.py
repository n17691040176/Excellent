from pydantic import Field

from app.schemas.common import AppBaseModel


class RegionAgentAuditRequest(AppBaseModel):
    approved: bool
    remark: str | None = Field(default=None, max_length=500)
    dividend_rate: float | None = Field(default=None, ge=0, le=100)


class RegionAgentRewardConfigRequest(AppBaseModel):
    dividend_rate: float = Field(ge=0, le=100)
