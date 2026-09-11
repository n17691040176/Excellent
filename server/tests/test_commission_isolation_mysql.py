"""Real row-lock and cross-mode balance checks on the explicitly configured local DB."""
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from test_city_partner import product_order

import app.main  # noqa: F401 - register ORM models
from app.core.exceptions import ConflictError
from app.models.city_partner import CityPartnerCommissionFlow, CityPartnerSeat
from app.models.commission import CommissionConfig, CommissionFlow, UserCommission
from app.models.enums import CommissionMode, CommissionStatus, GlobalRole, MemberLevel, OrderStatus, PayStatus
from app.models.order import Order
from app.models.product import ProductZoneConfig
from app.models.user import User
from app.services.catalog_service import ProductService
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.commission_service import CommissionService as Commissions
from app.services.order_service import OrderService

pytestmark = pytest.mark.skipif(not os.getenv('CITY_PARTNER_MYSQL_TEST_URL'), reason='Explicit local test database required')


@pytest.fixture
def engine():
    url = make_url(os.environ['CITY_PARTNER_MYSQL_TEST_URL'])
    assert url.host in {'127.0.0.1', 'localhost'} and url.database.endswith('_test')
    value = create_engine(url)
    yield value
    value.dispose()


def test_concurrent_city_creation_has_one_winner(engine):
    city_name = f'唯一席位-{uuid4().hex[:12]}'
    barrier = Barrier(2)
    def create():
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            barrier.wait(timeout=10)
            try:
                Seats.create_seat(db, '测试省', city_name, D('1000'), D('20'))
                return 'created'
            except ConflictError:
                db.rollback()
                return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(create) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == ['conflict', 'created']
    with Session(engine) as db:
        assert db.query(CityPartnerSeat).filter_by(province='测试省', city=city_name).count() == 1


def test_concurrent_old_and_new_settlement_preserves_shared_account(engine):
    previous_mode = None
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        parent = User(nickname='isolation-shared-parent', invite_code=uuid4().hex, password_hash='!', member_level=MemberLevel.DEALER)
        db.add(parent)
        db.flush()
        buyer = User(nickname='isolation-shared-buyer', invite_code=uuid4().hex, password_hash='!', parent_id=parent.id)
        db.add(buyer)
        db.commit()
        admin = db.query(User).filter_by(global_role=GlobalRole.SUPER_ADMIN).first()
        previous_mode = db.query(CommissionConfig).first().commission_mode
        parent_id, admin_id = parent.id, admin.id
        order_ids = []
        try:
            for mode in (CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER):
                _, rule, order = product_order(db, buyer)
                rule.custom_commission_enabled = True
                rule.custom_commission_method = 'FIXED_AMOUNT'
                rule.custom_commission_level2_enabled = True
                rule.custom_commission_level2_amount = D('8')
                db.commit()
                Commissions.update_commission_mode(db, mode, admin_id, 'MySQL isolation verification')
                OrderService._mark_paid(db, order)
                assert order.commission_mode == mode
                order.order_status = OrderStatus.COMPLETED
                order_ids.append(order.id)
                db.commit()
            assert db.query(UserCommission).filter_by(user_id=parent_id).one().frozen_amount == D('408')
        finally:
            db.rollback()
            Commissions.update_commission_mode(db, previous_mode, admin_id, 'Restore mode after local test setup')

    barrier = Barrier(2)
    def settle(order_id):
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            # Cache the same pre-settlement summary before either thread gets its lock.
            cached = db.query(UserCommission).filter_by(user_id=parent_id).one()
            assert cached.frozen_amount == D('408')
            barrier.wait(timeout=10)
            Commissions.settle_for_order(db, order_id)
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(settle, oid) for oid in order_ids]
        for future in futures:
            future.result(timeout=30)
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        balance = db.query(UserCommission).filter_by(user_id=parent_id).one()
        assert balance.available_amount == balance.total_amount == D('408') and balance.frozen_amount == 0
        assert db.query(CityPartnerCommissionFlow).filter_by(order_id=order_ids[0]).count() == 0
        assert db.query(CommissionFlow).filter_by(order_id=order_ids[1]).count() == 0
        Commissions.cancel_for_order(db, order_ids[0])
        db.commit()
        assert balance.available_amount == D('400')
        Commissions.cancel_for_order(db, order_ids[1])
        db.commit()
        assert balance.available_amount == balance.total_amount == 0


def prepare_order(db):
    parent = User(nickname='interleaved-parent', invite_code=uuid4().hex, password_hash='!', member_level=MemberLevel.DEALER)
    db.add(parent)
    db.flush()
    buyer = User(nickname='interleaved-buyer', invite_code=uuid4().hex, password_hash='!', parent_id=parent.id)
    db.add(buyer)
    db.flush()
    product, rule, order = product_order(db, buyer)
    rule.custom_commission_enabled = True
    rule.custom_commission_method = 'FIXED_AMOUNT'
    rule.custom_commission_level2_enabled = True
    rule.custom_commission_level2_amount = D('8')
    db.commit()
    return buyer, product, rule, order


@pytest.mark.parametrize('mode', [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER])
def test_mysql_refund_after_other_session_settles_cached_flows(engine, mode):
    flow_type = CommissionFlow if mode == CommissionMode.ORIGINAL else CityPartnerCommissionFlow
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        buyer, _, _, order = prepare_order(db)
        order.commission_mode = mode
        order.pay_status = PayStatus.PAID
        order.order_status = OrderStatus.COMPLETED
        db.flush()
        Commissions.freeze_for_order(db, order, buyer)
        db.commit()
        oid = order.id
        amounts = {}
        for flow in db.query(flow_type).filter_by(order_id=oid):
            if flow.beneficiary_user_id:
                amounts[flow.beneficiary_user_id] = amounts.get(flow.beneficiary_user_id, D('0')) + flow.commission_amount
        expected = {}
        for uid, amount in amounts.items():
            row = db.query(UserCommission).filter_by(user_id=uid).one()
            expected[uid] = (row.available_amount, row.frozen_amount - amount, row.total_amount - amount)
    cached, settled = Event(), Event()
    def refund():
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            flows = db.query(flow_type).filter_by(order_id=oid).all()
            assert all(f.status == CommissionStatus.FROZEN for f in flows)
            cached.set()
            assert settled.wait(timeout=15)
            assert all(f.status == CommissionStatus.FROZEN for f in flows)
            Commissions.cancel_for_order(db, oid)
            db.commit()
    def settle():
        assert cached.wait(timeout=15)
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            Commissions.settle_for_order(db, oid)
        settled.set()
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(refund), workers.submit(settle)]
        for future in futures:
            future.result(timeout=30)
    with Session(engine) as db:
        assert all(f.status == CommissionStatus.CANCELED for f in db.query(flow_type).filter_by(order_id=oid))
        for uid, balances in expected.items():
            row = db.query(UserCommission).filter_by(user_id=uid).one()
            assert (row.available_amount, row.frozen_amount, row.total_amount) == balances


def test_mysql_concurrent_partial_rule_edits_preserve_both_modes(engine):
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        _, product, _, _ = prepare_order(db)
        pid = product.id
        admin_id = db.query(User).filter_by(global_role=GlobalRole.SUPER_ADMIN).first().id
    barrier = Barrier(2)
    def edit(payload):
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            cached = db.query(ProductZoneConfig).filter_by(product_id=pid).one()
            admin = db.get(User, admin_id)
            barrier.wait(timeout=10)
            ProductService.update_zone_config_for_admin(db, pid, admin, payload)
            assert cached is not None
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(edit, payload) for payload in (
            {'city_partner_direct_reward_amount': D('300')}, {'custom_commission_level2_amount': D('11')})]
        for future in futures:
            future.result(timeout=30)
    with Session(engine) as db:
        rule = db.query(ProductZoneConfig).filter_by(product_id=pid).one()
        assert rule.custom_commission_level2_amount == D('11')
        assert rule.city_partner_direct_reward_amount == D('300')


@pytest.mark.parametrize('target_mode', [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER])
def test_mysql_payment_with_cached_mode_after_concurrent_switch(engine, target_mode):
    opposite = CommissionMode.CITY_PARTNER if target_mode == CommissionMode.ORIGINAL else CommissionMode.ORIGINAL
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        _, _, _, order = prepare_order(db)
        oid = order.id
        admin_id = db.query(User).filter_by(global_role=GlobalRole.SUPER_ADMIN).first().id
        original_mode = db.query(CommissionConfig).first().commission_mode
        Commissions.update_commission_mode(db, opposite, admin_id, 'Local interleaved payment setup')
    cached, switched = Event(), Event()
    def pay():
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            config = db.query(CommissionConfig).first()
            assert config.commission_mode == opposite
            order = db.get(Order, oid)
            cached.set()
            assert switched.wait(timeout=15)
            assert config.commission_mode == opposite
            OrderService._mark_paid(db, order)
            assert order.commission_mode == target_mode
    def switch():
        assert cached.wait(timeout=15)
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            Commissions.update_commission_mode(db, target_mode, admin_id, 'Local interleaved payment switch')
        switched.set()
    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(pay), workers.submit(switch)]
            for future in futures:
                future.result(timeout=30)
        with Session(engine) as db:
            old_count = db.query(CommissionFlow).filter_by(order_id=oid).count()
            new_count = db.query(CityPartnerCommissionFlow).filter_by(order_id=oid).count()
            assert (old_count > 0, new_count > 0) == (target_mode == CommissionMode.ORIGINAL, target_mode == CommissionMode.CITY_PARTNER)
    finally:
        with Session(engine) as db:
            Commissions.update_commission_mode(db, original_mode, admin_id, 'Restore mode after interleaved payment test')
