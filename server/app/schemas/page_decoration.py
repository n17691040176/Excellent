from app.schemas.common import AppBaseModel


class DecorationPayloadRequest(AppBaseModel):
    payload: dict = {}

