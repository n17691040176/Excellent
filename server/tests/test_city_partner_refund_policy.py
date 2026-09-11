"""Seat refunds are closed without blocking payment corrections or ordinary goods."""
from dataclasses import replace
from decimal import Decimal as D

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_city_partner import pay_seat, seat, user
from test_city_partner_recovery import db as shared_db

from app.api.deps.auth import get_current_user
from app.api.v1.mobile_serializers import serialize_admin_order, serialize_order
from app.api.v1.orders import admin_router, app_router
from app.core.exceptions import AppError, ConflictError
from app.db.session import get_db
from app.main import app_error_handler
from app.models.city_partner import CityPartnerPurchase, CityPartnerRotationFlow
from app.models.commission import CommissionConfig, UserCommission
from app.models.enums import (
    CommissionMode,
    GlobalRole,
    OrderStatus,
    PaymentChannel,
    PaymentStatus,
    PayStatus,
    RefundStatus,
)
from app.models.payment import PaymentRefund, PaymentTransaction
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

db = shared_db


def make_order(db, state):
    buyer = user(db, role=GlobalRole.SUPER_ADMIN)
    city = seat(db)
    if state == 'settled':
        return buyer, pay_seat(db, city, buyer)
    order = Seats.create_purchase_order(db, city.id, buyer, city.price_version)
    if state in {'failed', 'missing_purchase'}:
        city.price_version += 1
        db.commit()
        OrderService._mark_paid(db, order, external_paid_amount=D('1000'))
        if state == 'missing_purchase':
            db.delete(db.get(CityPartnerPurchase, order.id))
            db.commit()
    return buyer, order


@pytest.mark.parametrize('mode', [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER])
@pytest.mark.parametrize('state', ['unpaid', 'settled', 'failed', 'missing_purchase'])
def test_user_and_admin_cannot_refund_seat_in_either_mode(db, mode, state):
    buyer, order = make_order(db, state)
    db.query(CommissionConfig).first().commission_mode = mode
    db.commit()
    before = (order.pay_status, order.order_status, order.paid_amount)
    balances = [(r.user_id, r.available_amount, r.frozen_amount) for r in db.query(UserCommission).order_by(UserCommission.id)]
    rotations = db.query(CityPartnerRotationFlow).count()
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(app_router)
    app.include_router(admin_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: buyer
    with TestClient(app) as client:
        for scope in ('app', 'admin'):
            result = client.post(f'/{scope}/orders/{order.id}/refund', json={})
            assert result.status_code == 409, result.text
            assert result.json()['message'] == '城市合伙人订单不支持退款'
    for serializer in (serialize_order, serialize_admin_order):
        payload = serializer(db, order, include_detail=True)
        assert payload['can_refund'] is False
        assert payload['order']['can_refund'] is False
    db.refresh(order)
    assert (order.pay_status, order.order_status, order.paid_amount) == before
    assert db.query(PaymentRefund).count() == 0
    assert db.query(CityPartnerRotationFlow).count() == rotations
    assert [(r.user_id, r.available_amount, r.frozen_amount) for r in db.query(UserCommission).order_by(UserCommission.id)] == balances


def transaction(db, order, **kwargs):
    tx = PaymentTransaction(order_id=order.id, order_no=order.order_no, channel=PaymentChannel.WECHAT,
                            status=PaymentStatus.PAID, amount=D('1000'), out_trade_no=f'seat-policy-{order.id}', **kwargs)
    db.add(tx)
    db.commit()
    return tx


def test_direct_provider_refund_cannot_bypass_policy(db):
    _, order = make_order(db, 'failed')
    tx = transaction(db, order)
    with pytest.raises(ConflictError, match='城市合伙人订单不支持退款'):
        PaymentService.request_wechat_refund(db, order, tx)
    assert db.query(PaymentRefund).count() == 0
    assert order.pay_status == PayStatus.PAID


def test_unpaid_seat_can_still_be_canceled(db):
    _, order = make_order(db, 'unpaid')
    OrderService._cancel_order_instance(db, order, refunded=False)
    assert order.order_status == OrderStatus.REFUND
    assert order.pay_status == PayStatus.UNPAID
    assert db.query(PaymentRefund).count() == 0


def test_preexisting_provider_refund_can_finish_and_replay(db, monkeypatch):
    from app.services import payment_service as payment_module

    monkeypatch.setattr(payment_module, 'payment_config', replace(payment_module.payment_config, mock_external_payment=True))
    _, order = make_order(db, 'failed')
    tx = transaction(db, order)
    refund = PaymentRefund(order_id=order.id, order_no=order.order_no, payment_transaction_id=tx.id,
                           channel=PaymentChannel.WECHAT, status=RefundStatus.PENDING,
                           original_amount=D('1000'), refund_amount=D('1000'), out_refund_no='HISTORICAL-SEAT')
    db.add(refund)
    db.commit()
    assert PaymentService.request_wechat_refund(db, order, tx).status == RefundStatus.SUCCESS
    for _ in range(2):
        assert OrderService.sync_wechat_refund_for_order(db, order)['completed']
    assert order.pay_status == PayStatus.REFUNDED
    assert tx.refunded_amount == D('1000')
    assert db.query(PaymentRefund).count() == 1
    assert serialize_order(db, order, include_detail=True)['status_text'] == '已退款'


@pytest.mark.parametrize('state', ['unpaid', 'settled'])
def test_late_or_duplicate_payment_is_returned_without_reversing_seat(db, monkeypatch, state):
    from app.services import payment_service as payment_module

    monkeypatch.setattr(payment_module, 'payment_config', replace(payment_module.payment_config, mock_external_payment=True))
    _, order = make_order(db, state)
    if state == 'unpaid':
        OrderService._cancel_order_instance(db, order, refunded=False)
    tx = transaction(db, order, provider_trade_no='LATE-PAID', failed_reason='provider refund required')
    tx.status = PaymentStatus.FAILED
    db.commit()
    rotations = db.query(CityPartnerRotationFlow).count()
    for _ in range(2):
        refund = PaymentService.request_wechat_refund(db, order, tx)
        OrderService.finalize_external_refund(db, refund, tx)
    assert db.query(PaymentRefund).count() == 1
    assert tx.refunded_amount == D('1000')
    assert db.query(CityPartnerRotationFlow).count() == rotations
    assert order.pay_status == (PayStatus.PAID if state == 'settled' else PayStatus.REFUNDED)
