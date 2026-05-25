from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.api.v1.mobile_serializers import enum_value, iso_datetime, money
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.enums import GlobalRole, PaymentChannel, PaymentStatus
from app.models.payment import PaymentTransaction
from app.models.user import User
from app.services.payment_service import PaymentService

app_router = APIRouter(prefix='/payments')
admin_router = APIRouter(prefix='/admin/payments')


def _serialize_payment(tx: PaymentTransaction) -> dict[str, Any]:
    return {
        'id': tx.id,
        'payment_id': tx.id,
        'order_id': tx.order_id,
        'order_no': tx.order_no,
        'channel': enum_value(tx.channel),
        'status': enum_value(tx.status),
        'currency': tx.currency,
        'amount': money(tx.amount),
        'out_trade_no': tx.out_trade_no,
        'provider_trade_no': tx.provider_trade_no,
        'provider_app_id': tx.provider_app_id,
        'provider_payload': tx.provider_payload,
        'request_payload': tx.request_payload,
        'notify_payload': tx.notify_payload,
        'paid_at': iso_datetime(tx.paid_at),
        'failed_reason': tx.failed_reason,
        'created_at': iso_datetime(tx.created_at),
        'updated_at': iso_datetime(tx.updated_at),
    }


@app_router.post('/wechat/notify')
async def wechat_notify(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    PaymentService.handle_notify(db, PaymentChannel.WECHAT.value, payload)
    return JSONResponse({'code': 'SUCCESS', 'message': 'success'})


@app_router.post('/alipay/notify')
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    payload = dict(form.multi_items())
    PaymentService.handle_notify(db, PaymentChannel.ALIPAY.value, payload)
    return PlainTextResponse('success')


@admin_router.get('')
def admin_list_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order_no: str | None = Query(default=None),
    channel: PaymentChannel | None = Query(default=None),
    status: PaymentStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    query = db.query(PaymentTransaction)
    if order_no:
        query = query.filter(PaymentTransaction.order_no.ilike(f'%{order_no.strip()}%'))
    if channel:
        query = query.filter(PaymentTransaction.channel == channel)
    if status:
        query = query.filter(PaymentTransaction.status == status)

    safe_page = max(page, 1)
    safe_page_size = max(1, min(page_size, 100))
    total = query.order_by(None).count()
    rows = (
        query.order_by(PaymentTransaction.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'items': [_serialize_payment(row) for row in rows],
            'total': total,
            'page': safe_page,
            'page_size': safe_page_size,
        },
    }


@admin_router.get('/{payment_id}')
def admin_payment_detail(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    tx = db.get(PaymentTransaction, payment_id)
    if not tx:
        raise NotFoundError('Payment transaction not found')
    return {'code': 0, 'message': 'success', 'data': _serialize_payment(tx)}
