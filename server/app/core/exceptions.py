from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status


@dataclass
class AppError(Exception):
    message: str
    code: int = 40001
    status_code: int = status.HTTP_400_BAD_REQUEST
    data: Any = None


class UnauthorizedError(AppError):
    def __init__(self, message: str = 'Unauthorized') -> None:
        super().__init__(message=message, code=40101, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppError):
    def __init__(self, message: str = 'Forbidden') -> None:
        super().__init__(message=message, code=40301, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppError):
    def __init__(self, message: str = 'Not found') -> None:
        super().__init__(message=message, code=40401, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, message: str = 'Conflict') -> None:
        super().__init__(message=message, code=40901, status_code=status.HTTP_409_CONFLICT)


def raise_http_exc(message: str, status_code: int) -> None:
    raise HTTPException(status_code=status_code, detail=message)
