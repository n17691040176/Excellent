from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class APIResponse(AppBaseModel):
    code: int = 0
    message: str = 'success'
    data: dict | list | None = None
    request_id: str | None = None


class PaginationQuery(AppBaseModel):
    page: int = 1
    page_size: int = 20
