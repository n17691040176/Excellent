from app.schemas.common import AppBaseModel


class AdminPermissionUpdateRequest(AppBaseModel):
    permissions: list[str] = []
