import re

from pydantic import Field, field_validator

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


class SendLoginCodeRequest(AppBaseModel):
    phone: str = Field(min_length=6, max_length=20)


class CodeLoginRequest(AppBaseModel):
    phone: str = Field(min_length=6, max_length=20)
    code: str = Field(min_length=4, max_length=8)
    invite_code: str | None = Field(default=None, max_length=32)


class ResetPasswordRequest(AppBaseModel):
    phone: str
    new_password: str = Field(min_length=6, max_length=64)


class OneClickLoginRequest(AppBaseModel):
    """一键登录请求"""
    access_token: str  # 阿里云 SDK 返回的令牌


class OneClickRegisterRequest(AppBaseModel):
    """一键登录新用户注册请求"""
    access_token: str
    nickname: str = Field(min_length=1, max_length=64)
    invite_code: str | None = Field(default=None, max_length=32)


class AppLoginRequest(AppBaseModel):
    """App端传递手机号免注册登录"""
    phone: str = Field(min_length=11, max_length=11, description="手机号（App端已验证）")
    nickname: str | None = Field(default=None, max_length=64, description="昵称（首次登录时可选）")
    invite_code: str | None = Field(default=None, max_length=32, description="邀请码")

    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, value) -> str:
        phone = str(value or '').strip()
        if not re.fullmatch(r'1[3-9]\d{9}', phone):
            raise ValueError('手机号格式不正确')
        return phone
