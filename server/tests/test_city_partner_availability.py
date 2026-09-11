from dataclasses import replace

import pytest
from fastapi import Response
from sqlalchemy import update
from test_city_partner import db as shared_db
from test_city_partner import seat, user

from app.api.v1.admin_city_partners import city_partner_availability, list_public_seats
from app.api.v1.mobile_serializers import serialize_order
from app.core.exceptions import ConflictError
from app.models.commission import CommissionConfig
from app.models.enums import CommissionMode, OrderStatus, PayStatus
from app.models.order import Order
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService, payment_config

# Re-export the shared pytest fixture without shadowing an unused import.
db = shared_db


def switch(db, mode):
    # Deliberately leave an already-loaded config stale in the identity map.
    db.execute(update(CommissionConfig).values(commission_mode=mode).execution_options(synchronize_session=False))
    db.commit()


def test_mobile_visibility_and_order_creation_follow_mode_switches(db):
    buyer, city = user(db), seat(db)
    cached = db.query(CommissionConfig).first()
    response = Response()
    assert city_partner_availability(response, db)['data']['enabled'] is True
    assert response.headers['cache-control'] == 'no-store'
    assert list_public_seats(db, buyer)['data']['total'] == 1
    switch(db, CommissionMode.ORIGINAL)
    assert cached.commission_mode == CommissionMode.CITY_PARTNER
    assert city_partner_availability(Response(), db)['data']['enabled'] is False
    assert list_public_seats(db, buyer)['data'] == {'enabled': False, 'items': [], 'total': 0}
    with pytest.raises(ConflictError, match='暂未开放'):
        Seats.create_purchase_order(db, city.id, buyer, city.price_version)
    db.rollback()
    assert db.query(Order).count() == 0
    assert len(Seats.list_seats(db)) == 1  # Admin management remains available.
    switch(db, CommissionMode.CITY_PARTNER)
    assert list_public_seats(db, buyer)['data']['total'] == 1
    assert Seats.create_purchase_order(db, city.id, buyer, city.price_version).id


@pytest.mark.parametrize('payment_entry', ['external', 'demo', 'internal'])
def test_disabled_mode_blocks_unpaid_seat_payment_without_changing_order(db, monkeypatch, payment_entry):
    buyer, city = user(db), seat(db)
    order = Seats.create_purchase_order(db, city.id, buyer, city.price_version)
    switch(db, CommissionMode.ORIGINAL)
    assert serialize_order(db, order)['can_pay'] is False
    config = replace(payment_config, mock_external_payment=True)
    monkeypatch.setattr('app.services.payment_service.payment_config', config)
    monkeypatch.setattr('app.services.order_service.payment_config', config)
    with pytest.raises(ConflictError, match='暂未开放'):
        if payment_entry == 'external':
            PaymentService.prepare_external_payment(db, order, 'WECHAT')
        elif payment_entry == 'demo':
            OrderService.pay_order_for_user(db, buyer.id, order.id)
        else:
            OrderService.pay_order(db, buyer, order.id, 'BALANCE')
    db.rollback()
    assert order.pay_status == PayStatus.UNPAID
    assert order.order_status == OrderStatus.PENDING_PAYMENT
    assert city.current_user_id is None


def test_previously_initiated_payment_can_finish_after_switch(db):
    buyer, city = user(db), seat(db)
    order = Seats.create_purchase_order(db, city.id, buyer, city.price_version)
    switch(db, CommissionMode.ORIGINAL)
    # Provider funds already received: preserve fulfilment and callback idempotence.
    OrderService._mark_paid(db, order, external_paid_amount=order.total_amount)
    OrderService._mark_paid(db, order, external_paid_amount=order.total_amount)
    assert order.pay_status == PayStatus.PAID
    assert order.order_status == OrderStatus.COMPLETED
    assert city.current_user_id == buyer.id
    assert serialize_order(db, order)['id'] == order.id


def test_missing_mode_config_defaults_to_closed(db):
    db.query(CommissionConfig).delete()
    db.commit()
    assert Seats.mobile_enabled(db) is False
