from pydantic import Field, field_validator

from app.schemas.common import AppBaseModel


class BankCardCreateRequest(AppBaseModel):
    holder_name: str = Field(min_length=2, max_length=64)
    bank_name: str = Field(min_length=2, max_length=128)
    branch_name: str | None = Field(default=None, max_length=255)
    card_number: str = Field(min_length=12, max_length=30)
    is_default: bool = False

    @field_validator('holder_name', 'bank_name', 'branch_name', mode='before')
    @classmethod
    def clean_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('card_number')
    @classmethod
    def validate_card_number(cls, value: str) -> str:
        normalized = ''.join(char for char in value if char.isdigit())
        if not 12 <= len(normalized) <= 30:
            raise ValueError('Bank card number must contain 12 to 30 digits')
        return normalized


class BankCardUpdateRequest(AppBaseModel):
    holder_name: str | None = Field(default=None, min_length=2, max_length=64)
    bank_name: str | None = Field(default=None, min_length=2, max_length=128)
    branch_name: str | None = Field(default=None, max_length=255)
    card_number: str | None = Field(default=None, min_length=12, max_length=30)
    is_default: bool | None = None

    @field_validator('holder_name', 'bank_name', 'branch_name', mode='before')
    @classmethod
    def clean_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('card_number')
    @classmethod
    def validate_card_number(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = ''.join(char for char in value if char.isdigit())
        if not 12 <= len(normalized) <= 30:
            raise ValueError('Bank card number must contain 12 to 30 digits')
        return normalized
