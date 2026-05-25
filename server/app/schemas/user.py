from app.schemas.common import AppBaseModel


class UserOut(AppBaseModel):
    id: int
    phone: str | None = None
    nickname: str
    avatar: str | None = None
    global_role: str
    business_identity: str
    status: str
    invite_code: str
    team_id: int | None = None


class UpdateProfileRequest(AppBaseModel):
    nickname: str | None = None
    avatar: str | None = None
    real_name: str | None = None


class UpdateUserStatusRequest(AppBaseModel):
    status: str
