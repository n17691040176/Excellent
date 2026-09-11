from copy import deepcopy
from decimal import Decimal as D

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_city_partner import pay_seat, product_order, seat, summary, user

from app.api.deps.auth import get_current_user
from app.api.v1.commission import admin_router
from app.api.v1.mobile_serializers import serialize_order
from app.core.exceptions import AppError, ConflictError
from app.db.base import Base
from app.db.session import get_db
from app.main import app_error_handler
from app.models.city_partner import CityPartnerCommissionFlow, CityPartnerRotationFlow
from app.models.commission import CommissionConfig, CommissionFlow, UserCommission
from app.models.enums import CommissionMode, GlobalRole, OrderStatus, PaymentChannel, PaymentStatus, PayStatus
from app.models.order import OrderItem
from app.models.payment import PaymentTransaction
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.commission_accounts import ensure_system_accounts
from app.services.commission_audit import list_rule_changes
from app.services.commission_service import CommissionService as Commissions
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.utils.helpers import now


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        ensure_system_accounts(session)
        session.add(CommissionConfig(commission_mode=CommissionMode.CITY_PARTNER, updated_at=now()))
        session.commit()
        yield session
    engine.dispose()


def pending_payment(db, shipping=True):
    buyer = user(db, role=GlobalRole.SUPER_ADMIN)
    product, rule, order = product_order(db, buyer, shipping=shipping)
    product.sale_price, product.cost_price = D('2000'), D('1000')
    transaction = PaymentTransaction(order_id=order.id, order_no=order.order_no,
                                     channel=PaymentChannel.ALIPAY, amount=order.total_amount,
                                     out_trade_no=f'recovery-{order.id}')
    db.add(transaction)
    db.commit()
    return buyer, product, rule, order, transaction


@pytest.mark.parametrize('shipping', [True, False])
def test_failed_allocation_retains_payment_snapshot_and_refunds_once(db, shipping):
    buyer, product, rule, order, tx = pending_payment(db, shipping)
    before_stock = product.stock
    PaymentService.confirm_paid_order(db, tx, {'mocked': True}, 'verified-trade')
    assert tx.status == PaymentStatus.PAID and tx.provider_trade_no == 'verified-trade'
    assert order.pay_status == PayStatus.PAID and order.paid_amount == D('1600')
    assert order.order_status == OrderStatus.PENDING_SHIP and order.confirmed_at is None
    assert order.mode_locked_at is not None
    snapshot = deepcopy(order.city_partner_rule_snapshot)
    assert snapshot['items'][0]['unit_sale'] == '1600.00'
    assert snapshot['items'][0]['unit_cost'] == '1000.00'
    assert 'profit pool' in snapshot['settlement_error']
    assert order.profit_pool_snapshot == D('600')
    assert Commissions.list_failed_settlements(db)['total'] == 1
    assert db.query(CityPartnerCommissionFlow).count() == db.query(CommissionFlow).count() == 0
    serialized = serialize_order(db, order, include_detail=True)
    assert serialized['commission_pending_review'] and serialized['can_refund']
    assert not serialized['can_confirm'] and serialized['order']['commission_pending_review']

    # Replayed payment callbacks and edits cannot silently recalculate a failed order.
    product.cost_price = D('500')
    rule.city_partner_amount = D('0')
    db.query(CommissionConfig).first().commission_mode = CommissionMode.ORIGINAL
    db.commit()
    PaymentService.confirm_paid_order(db, tx, {'mocked': True}, 'verified-trade')
    OrderService._mark_paid(db, order)
    assert order.commission_mode == CommissionMode.CITY_PARTNER
    assert order.city_partner_rule_snapshot == snapshot
    for action in (
        lambda: OrderService.ship_order_for_admin(db, order.id, buyer, 'TRACK'),
        lambda: OrderService._confirm_order_instance(db, order),
        lambda: Commissions.freeze_for_order(db, order, buyer),
        lambda: Commissions.settle_for_order(db, order.id),
    ):
        with pytest.raises(ConflictError, match='manual refund'):
            action()
        db.rollback()

    assert OrderService.refund_order_with_result(db, order)['completed']
    assert OrderService.refund_order_with_result(db, order)['completed']
    assert order.pay_status == PayStatus.REFUNDED
    assert product.stock == before_stock + 1
    assert order.city_partner_rule_snapshot == snapshot
    assert Commissions.list_failed_settlements(db)['total'] == 0
    assert not serialize_order(db, order)['commission_pending_review']
    assert all(row.total_amount == 0 for row in db.query(UserCommission).all())


def test_later_invalid_item_rolls_back_entire_commission_plan(db):
    buyer, product, _, order, tx = pending_payment(db)
    good, _, extra_order = product_order(db, buyer)
    product.cost_price, good.cost_price = D('700'), D('1000')
    item = db.query(OrderItem).filter_by(order_id=extra_order.id).one()
    item.order_id = order.id
    order.total_amount += D('1600')
    order.payable_amount = order.total_amount
    tx.amount = order.total_amount
    db.commit()
    PaymentService.confirm_paid_order(db, tx, {'mocked': True})
    assert len(order.city_partner_rule_snapshot['items']) == 2
    assert order.sale_price_snapshot == D('3200')
    assert order.cost_price_snapshot == D('1700')
    assert db.query(CityPartnerCommissionFlow).count() == 0
    assert all(row.frozen_amount == 0 for row in db.query(UserCommission).all())


def test_partial_account_writes_are_rolled_back_on_business_failure(db, monkeypatch):
    buyer = user(db)
    _, _, order = product_order(db, buyer)
    original = Commissions._add_city_partner_flow

    def fail_after_credit(*args):
        original(*args)
        raise ConflictError('injected account allocation rejection')

    monkeypatch.setattr(Commissions, '_add_city_partner_flow', fail_after_credit)
    OrderService._mark_paid(db, order)
    assert order.pay_status == PayStatus.PAID
    assert 'account allocation rejection' in Commissions.settlement_failure(order)
    assert db.query(CityPartnerCommissionFlow).count() == 0
    assert all(row.frozen_amount == row.total_amount == 0 for row in db.query(UserCommission).all())


@pytest.mark.parametrize('role,expected', [(GlobalRole.USER, 403), (GlobalRole.TEAM_ADMIN, 403), (GlobalRole.SUPER_ADMIN, 200)])
def test_failed_settlements_api_is_super_admin_only(db, role, expected):
    _, _, _, order, tx = pending_payment(db)
    PaymentService.confirm_paid_order(db, tx, {'mocked': True})
    actor = user(db, role=role)
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(admin_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: actor
    with TestClient(app) as client:
        response = client.get('/admin/commission/failed-settlements')
    assert response.status_code == expected
    if expected == 200:
        assert response.json()['data']['items'][0]['order_id'] == order.id


@pytest.mark.parametrize('cap', [D('2000'), None])
def test_reopen_capped_seat_preserves_history_and_audits_quote(db, cap):
    city = seat(db, price_cap=D('1100'))
    first = pay_seat(db, city, user(db))
    second = pay_seat(db, city, user(db))
    old_flows = [(flow.new_price, flow.principal_refund_amount) for flow in db.query(CityPartnerRotationFlow).all()]
    old_version, holder = city.price_version, city.current_user_id
    admin = user(db)
    Seats.update_seat(db, city.id, D('20'), cap, 'ACTIVE', operator_id=admin.id, change_reason='恢复报价')
    assert city.current_price == D('1320') and city.price_version == old_version + 1
    assert city.current_user_id == holder and city.current_order_id == second.id
    assert first.paid_amount == D('1000') and second.paid_amount == D('1100')
    assert [(flow.new_price, flow.principal_refund_amount) for flow in db.query(CityPartnerRotationFlow).all()] == old_flows
    change = list_rule_changes(db, 'SEAT', city.id)['items'][0]
    assert D(change['before_values']['current_price']) == D('1100')
    assert D(change['after_values']['current_price']) == D('1320')
    assert change['operator_id'] == admin.id
    with pytest.raises(ConflictError, match='quote changed'):
        Seats.create_purchase_order(db, city.id, user(db), old_version)
    next_order = pay_seat(db, city, user(db))
    flow = db.query(CityPartnerRotationFlow).filter_by(order_id=next_order.id).one()
    assert flow.principal_refund_amount == D('1100')
    assert flow.appreciation_reward_amount == D('88')
    assert summary(db, holder).available_amount == D('1188')


def test_reopening_keeps_cap_and_rounding_constraints(db):
    city = seat(db, price_cap=D('1100'))
    pay_seat(db, city, user(db))
    pay_seat(db, city, user(db))
    Seats.update_seat(db, city.id, D('50'), D('1150'), 'ACTIVE')
    assert city.current_price == D('1150')
    pay_seat(db, city, user(db))
    with pytest.raises(ConflictError, match='price cap'):
        Seats.create_purchase_order(db, city.id, user(db), city.price_version)
