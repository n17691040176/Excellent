from typing import Literal

from pydantic import Field

from app.schemas.common import AppBaseModel


DataScope = Literal['ALL', 'TEAM']
EnabledStatus = Literal['ENABLED', 'DISABLED']


class AdminRoleCreateRequest(AppBaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r'^[A-Z][A-Z0-9_]*$')
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    data_scope: DataScope = 'TEAM'
    permissions: list[str] = Field(default_factory=list)


class AdminRoleUpdateRequest(AppBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    data_scope: DataScope | None = None
    status: EnabledStatus | None = None
    permissions: list[str] | None = None


class AdminCreateRequest(AppBaseModel):
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(min_length=1, max_length=64)
    role_id: int
    team_id: int | None = None


class AdminPromoteRequest(AppBaseModel):
    user_id: int
    role_id: int
    team_id: int | None = None


class AdminUpdateRequest(AppBaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=64)
    role_id: int | None = None
    team_id: int | None = None


class AdminStatusRequest(AppBaseModel):
    status: EnabledStatus


class AdminResetPasswordRequest(AppBaseModel):
    new_password: str = Field(min_length=8, max_length=64)


class AdminProfileUpdateRequest(AppBaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=64)
    avatar: str | None = Field(default=None, max_length=255)
    real_name: str | None = Field(default=None, max_length=64)


class AdminChangePasswordRequest(AppBaseModel):
    current_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)
