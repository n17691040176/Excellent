"""Opt-in concurrency check. Adds labeled records to a local test database."""
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import app.main  # noqa: F401
from app.core.exceptions import ConflictError
from app.models.city_partner import CityPartnerPurchase, CityPartnerRotationFlow
from app.models.enums import OrderStatus, PayStatus
from app.models.order import Order
from app.models.user import User
from app.services.city_partner_service import CityPartnerService
from app.services.order_service import OrderService


@pytest.mark.skipif(not os.getenv('CITY_PARTNER_MYSQL_TEST_URL'), reason='Requires an explicit local MySQL test database')
def test_mysql_concurrent_payments_allocate_exactly_one_seat():
    url = make_url(os.environ['CITY_PARTNER_MYSQL_TEST_URL'])
    assert url.host in {'127.0.0.1', 'localhost'} and url.database.endswith('_test')
    engine = create_engine(url)
    try:
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            buyers = [User(nickname=f'concurrency-test-{i}', invite_code=uuid4().hex,
                           password_hash='!') for i in range(2)]
            db.add_all(buyers)
            db.commit()
            seat = CityPartnerService.create_seat(db, '测试省', f'并发验证-{uuid4().hex}', Decimal('1000'), Decimal('20'))
            seat_id = seat.id
            order_ids = [CityPartnerService.create_purchase_order(db, seat.id, buyer, 0).id for buyer in buyers]

        def pay(order_id):
            with Session(engine, autoflush=False, expire_on_commit=False) as db:
                order = OrderService._mark_paid(db, db.get(Order, order_id), external_paid_amount=Decimal('1000'))
                return order.pay_status, order.order_status

        with ThreadPoolExecutor(max_workers=2) as workers:
            states = list(workers.map(pay, order_ids))
        assert all(paid == PayStatus.PAID for paid, _ in states)
        assert sum(status == OrderStatus.COMPLETED for _, status in states) == 1
        with Session(engine) as db:
            flows = db.query(CityPartnerRotationFlow).filter_by(seat_id=seat_id).all()
            assert len(flows) == 1
            flow = flows[0]
            assert flow.new_price == flow.company_amount == Decimal('1000')
            pending = db.query(CityPartnerPurchase).filter(
                CityPartnerPurchase.order_id.in_(order_ids), CityPartnerPurchase.settled_at.is_(None),
            ).one()
            assert pending.settlement_error
            with pytest.raises(ConflictError, match='城市合伙人订单不支持退款'):
                OrderService._validate_paid_refund_transition(db, db.get(Order, pending.order_id))
    finally:
        engine.dispose()


@pytest.mark.skipif(not os.getenv('CITY_PARTNER_MYSQL_TEST_URL'), reason='Requires an explicit local MySQL test database')
def test_mysql_retains_raw_fractional_cents_and_audit_history():
    from test_city_partner import product_order

    from app.models.city_partner import CityPartnerCommissionFlow
    from app.models.enums import CommissionMode, GlobalRole
    from app.schemas.product import ProductZoneConfigUpdateRequest
    from app.services.catalog_service import ProductService
    from app.services.commission_audit import list_rule_changes
    from app.services.commission_service import CommissionService

    url = make_url(os.environ['CITY_PARTNER_MYSQL_TEST_URL'])
    assert url.host in {'127.0.0.1', 'localhost'} and url.database.endswith('_test')
    engine = create_engine(url)
    try:
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            parent = None
            for level in range(9):
                buyer = User(nickname=f'document-precision-{level}', invite_code=uuid4().hex, password_hash='!',
                             parent_id=parent.id if parent else None)
                db.add(buyer)
                db.flush()
                parent = buyer
            product, _, order = product_order(db, buyer)
            product.product_name = f'document-precision-{uuid4().hex[:8]}'
            order.commission_mode = CommissionMode.CITY_PARTNER
            order.pay_status = PayStatus.PAID
            db.flush()
            CommissionService.freeze_for_order(db, order, buyer)
            db.commit()
            db.expire_all()
            flow = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id, commission_role='UPLINE', level=7).one()
            assert flow.calculated_amount == Decimal('3.125')
            assert flow.commission_amount == Decimal('3.12')
            assert flow.calculation_precision_known
            admin = db.query(User).filter(User.global_role == GlobalRole.SUPER_ADMIN).first()
            assert admin is not None
            listed = CommissionService.list_flows_page_for_admin(db, admin, keyword=order.order_no)['items']
            assert next(item for item in listed if item['commission_role'] == 'UPLINE' and item['level'] == 7)['calculated_amount'] == '3.125'
            payload = ProductZoneConfigUpdateRequest(city_partner_commission_enabled=True, city_partner_amount=100,
                                                      change_reason='MySQL audit verification').model_dump()
            ProductService.update_zone_config_for_admin(db, product.id, admin, payload)
            db.expire_all()
            changes = list_rule_changes(db, 'PRODUCT', product.id)['items']
            assert changes[0]['operator_id'] == admin.id
            assert changes[0]['reason'] == 'MySQL audit verification'
            assert Decimal(changes[0]['before_values']['city_partner_direct_reward_amount']) == Decimal('400')
            assert db.get(CityPartnerCommissionFlow, flow.id).calculated_amount == Decimal('3.125')
    finally:
        engine.dispose()


@pytest.mark.skipif(not os.getenv('CITY_PARTNER_MYSQL_TEST_URL'), reason='Requires an explicit local MySQL test database')
def test_mysql_manual_upline_exact_amounts_and_snapshot():
    from test_city_partner import product_order

    from app.models.city_partner import CityPartnerCommissionFlow
    from app.models.enums import CommissionMode, GlobalRole
    from app.schemas.product import ProductZoneConfigUpdateRequest
    from app.services.catalog_service import ProductService
    from app.services.commission_service import CommissionService

    url = make_url(os.environ['CITY_PARTNER_MYSQL_TEST_URL'])
    assert url.host in {'127.0.0.1', 'localhost'} and url.database.endswith('_test')
    engine = create_engine(url)
    try:
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            parent = None
            for level in range(9):
                buyer = User(nickname=f'manual-upline-test-{level}', invite_code=uuid4().hex,
                             password_hash='!', parent_id=parent.id if parent else None)
                db.add(buyer)
                db.flush()
                parent = buyer
            product, config, order = product_order(db, buyer, quantity=3)
            product.product_name = f'manual-upline-test-{uuid4().hex[:8]}'
            admin = db.query(User).filter(User.global_role == GlobalRole.SUPER_ADMIN).first()
            assert admin is not None
            ProductService.update_zone_config_for_admin(db, product.id, admin,
                ProductZoneConfigUpdateRequest(city_partner_upline_mode='MANUAL',
                    city_partner_upline_amounts=['0.20'] * 7).model_dump(exclude_unset=True))
            db.expire_all()
            assert config.city_partner_upline_mode == 'MANUAL'
            assert config.city_partner_upline_amounts == ['0.20'] * 7
            order.commission_mode = CommissionMode.CITY_PARTNER
            order.pay_status = PayStatus.PAID
            db.flush()
            CommissionService.freeze_for_order(db, order, buyer)
            db.commit()
            db.expire_all()
            flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id, commission_role='UPLINE').all()
            assert len(flows) == 7
            assert all(f.commission_amount == f.calculated_amount == Decimal('0.60') for f in flows)
            snapshot = order.city_partner_rule_snapshot['items'][0]['rule']
            assert snapshot['city_partner_calculation_policy'] == 'MANUAL_7_V1'
            assert snapshot['city_partner_upline_amounts'] == ['0.20'] * 7
    finally:
        engine.dispose()
