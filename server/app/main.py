import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logger import configure_logging
from app.core.payment_config import validate_payment_config
from app.core.redis import get_redis_client
from app.db.init_db import init_db
from app.db.migrations import apply_schema_migrations
from app.db.seed import seed_defaults
from app.db.session import SessionLocal
from app.services.page_decoration_service import PageDecorationService
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)
WECHAT_REFUND_RECONCILIATION_INTERVAL_SECONDS = 60


def _reconcile_due_wechat_refunds() -> None:
    db = SessionLocal()
    try:
        PaymentService.reconcile_due_wechat_refunds(db)
    finally:
        db.close()


async def _wechat_refund_reconciliation_loop() -> None:
    """Keep provider refunds convergent even if a webhook is unavailable."""
    while True:
        try:
            await asyncio.to_thread(_reconcile_due_wechat_refunds)
        except Exception:
            logger.exception('WeChat refund reconciliation pass failed')
        await asyncio.sleep(WECHAT_REFUND_RECONCILIATION_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    validate_payment_config(settings.app_env)
    PageDecorationService.upload_root()
    init_db()
    apply_schema_migrations()
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()
    refund_reconciliation_task = asyncio.create_task(_wechat_refund_reconciliation_loop())
    try:
        yield
    finally:
        refund_reconciliation_task.cancel()
        with suppress(asyncio.CancelledError):
            await refund_reconciliation_task


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
    services = {'mysql': 'ok', 'redis': 'ok'}
    status_code = 200

    db = SessionLocal()
    try:
        db.execute(text('SELECT 1'))
    except Exception:
        services['mysql'] = 'error'
        status_code = 503
    finally:
        db.close()

    try:
        get_redis_client().ping()
    except Exception:
        services['redis'] = 'error'
        status_code = 503

    return ORJSONResponse(
        status_code=status_code,
        content={
            'code': 0 if status_code == 200 else 50001,
            'message': 'success' if status_code == 200 else 'dependency unavailable',
            'data': {
                'status': 'ok' if status_code == 200 else 'degraded',
                'services': services,
            },
        },
    )


app.include_router(api_router)
