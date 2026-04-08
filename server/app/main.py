from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logger import configure_logging
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.db.seed import seed_defaults
from app.services.page_decoration_service import PageDecorationService


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    PageDecorationService.upload_root()
    init_db()
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, debug=settings.app_debug, lifespan=lifespan)
app.mount('/uploads', StaticFiles(directory=str(PageDecorationService.upload_root())), name='uploads')

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get('X-Request-Id') or uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers['X-Request-Id'] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            'code': exc.code,
            'message': exc.message,
            'data': exc.data,
            'request_id': getattr(request.state, 'request_id', None),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return ORJSONResponse(
        status_code=422,
        content={
            'code': 40001,
            'message': 'Parameter validation failed',
            'data': exc.errors(),
            'request_id': getattr(request.state, 'request_id', None),
        },
    )


@app.get('/health')
def health():
    return {'code': 0, 'message': 'success', 'data': {'status': 'ok'}}


app.include_router(api_router)
