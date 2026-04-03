from pydantic import Field

from app.schemas.common import AppBaseModel


class TokenResponse(AppBaseModel):
    access_token: str
    token_type: str = 'bearer'


class RegisterRequest(AppBaseModel):
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(min_length=1, max_length=64)
    invite_code: str | None = Field(default=None, max_length=32)


class LoginRequest(AppBaseModel):
    phone: str
    password: str


class ResetPasswordRequest(AppBaseModel):
    phone: str
    new_password: str = Field(min_length=6, max_length=64)
