from app.schemas.common import AppBaseModel


class TeamCreateRequest(AppBaseModel):
    name: str
    description: str | None = None


class TeamUpdateRequest(AppBaseModel):
    name: str | None = None
    description: str | None = None


class TeamRoleUpdateRequest(AppBaseModel):
    team_role: str
