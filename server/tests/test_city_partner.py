from decimal import Decimal as D

import pytest
from pydantic import ValidationError
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

import app.main  # noqa: F401
from app.api.v1.mobile_serializers import serialize_commission_flow, serialize_order
from app.core.exceptions import ConflictError
from app.db.base import Base
from app.models.address import UserAddress
from app.models.city_partner import (
    CityPartnerCommissionFlow,
    CityPartnerPurchase,
    CityPartnerRotationFlow,
)
from app.models.commission import CommissionConfig, UserCommission
from app.models.enums import (
    CommissionMode,
    CommissionStatus,
    GlobalRole,
    OrderStatus,
    OrderType,
    PayStatus,
    ProductOwnerType,
    ProductType,
    ZoneType,
)
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductZoneConfig
from app.models.user import User
from app.schemas.product import ProductZoneConfigUpdateRequest
from app.services.catalog_service import ProductService
from app.services.city_partner_rules import validate_city_partner_rule
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.commission_accounts import ensure_system_accounts, system_account
from app.services.commission_service import CommissionService as Commissions
from app.services.order_service import OrderService
from app.services.region_dividend_service import RegionDividendService
from app.utils.helpers import now


@compiles(BigInteger, 'sqlite')
def sqlite_bigint(_element, _compiler, **_kwargs):
    return 'INTEGER'


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        ensure_system_accounts(session)
        session.add(CommissionConfig(commission_mode=CommissionMode.CITY_PARTNER, updated_at=now()))
        session.commit()
        yield session
    engine.dispose()


def user(db, parent=None, role=GlobalRole.USER, team_id=None):
    number = db.query(User).count() + 1
    row = User(
        nickname=f'user-{number}',
        invite_code=f'invite-{number}',
        password_hash='test',
        global_role=role,
        parent_id=parent.id if parent else None,
        team_id=team_id,
    )
    db.add(row)
    db.flush()
    db.add(UserCommission(user_id=row.id, updated_at=now()))
    db.commit()
    return row


def summary(db, uid):
    return db.query(UserCommission).filter_by(user_id=uid).one()


def seat(db, city='西安市', **kwargs):
    return Seats.create_seat(db, '陕西省', city, D('1000'), D('20'), **kwargs)


def pay_seat(db, city_seat, buyer):
    order = Seats.create_purchase_order(db, city_seat.id, buyer, city_seat.price_version)
    OrderService._mark_paid(db, order, external_paid_amount=order.total_amount)
    return order


def product_order(db, buyer, *, quantity=1, shipping=True, **rule_changes):
    p = Product(
        product_name='test',
        product_type=ProductType.PHYSICAL,
        owner_type=ProductOwnerType.SELF_OPERATED,
        zone_type=ZoneType.SELF_OPERATED,
        sale_price=D('1600'),
        cost_price=D('700'),
        stock=100,
        requires_shipping=shipping,
    )
    db.add(p)
    db.flush()
    rules = {
        'city_partner_commission_enabled': True,
        'city_partner_amount': D('100'),
        'city_partner_direct_reward_amount': D('400'),
        'city_partner_upline_initial_amount': D('200'),
    }
    rules.update(rule_changes)
    config = ProductZoneConfig(product_id=p.id, zone_type=p.zone_type, **rules)
    address = UserAddress(
        user_id=buyer.id,
        receiver_name='test',
        receiver_phone='19900000000',
        province='陕西省',
        city='西安市',
        district='雁塔区',
        detail_address='test',
    )
    db.add_all([config, address])
    db.flush()
    oid = db.query(Order).count() + 1
    order = Order(
        order_no=f'TEST-{oid}',
        user_id=buyer.id,
        team_id=buyer.team_id,
        order_type=OrderType.SELF_OPERATED_ORDER,
        total_amount=p.sale_price * quantity,
        payable_amount=p.sale_price * quantity,
        legacy_address_id=address.id,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=p.id,
            product_name=p.product_name,
            unit_price=p.sale_price,
            quantity=quantity,
            total_amount=p.sale_price * quantity,
            created_at=now(),
        )
    )
    db.commit()
    return p, config, order


def test_ordinary_order_cannot_buy_any_seat(db):
    buyer = user(db)
    _, _, order = product_order(db, buyer)
    city_seat = seat(db)
    order.paid_amount = D('1000')
    order.pay_status = PayStatus.PAID
    db.commit()
    with pytest.raises(ConflictError, match='dedicated purchase'):
        Seats.purchase_or_rotate(db, city_seat.id, buyer, order.id)
    assert db.query(CityPartnerRotationFlow).count() == 0


def test_seat_purchase_is_atomic_idempotent_and_cannot_cross_cities(db):
    parent = user(db)
    buyer = user(db, parent)
    a, b = seat(db), seat(db, '咸阳市')
    order = pay_seat(db, a, buyer)
    assert order.order_status == OrderStatus.COMPLETED
    assert a.current_user_id == buyer.id
    assert summary(db, parent.id).available_amount == D('100')
    assert summary(db, system_account(db, 'COMPANY').id).available_amount == D('900')
    Seats.purchase_or_rotate(db, a.id, buyer, order.id)
    assert db.query(CityPartnerRotationFlow).count() == 1
    assert summary(db, parent.id).available_amount == D('100')
    with pytest.raises(ConflictError, match='dedicated purchase'):
        Seats.purchase_or_rotate(db, b.id, buyer, order.id)
    assert b.current_user_id is None


def test_rotation_credits_all_accounts_and_conserves_payment(db):
    previous = user(db)
    parent = user(db)
    buyer = user(db, parent)
    city_seat = seat(db)
    pay_seat(db, city_seat, previous)
    second = pay_seat(db, city_seat, buyer)
    flow = db.query(CityPartnerRotationFlow).filter_by(order_id=second.id).one()
    assert summary(db, previous.id).available_amount == D('1080')
    assert summary(db, parent.id).available_amount == D('20')
    assert summary(db, system_account(db, 'COMPANY').id).available_amount == D('1060')
    assert summary(db, system_account(db, 'OPERATIONS').id).available_amount == D('40')
    assert sum(
        [
            flow.principal_refund_amount,
            flow.appreciation_reward_amount,
            flow.company_amount,
            flow.parent_reward_amount,
            flow.operations_amount,
        ]
    ) == D('1200')


@pytest.mark.parametrize('legacy', [False, True])
def test_successful_seat_refund_is_rejected_before_side_effects(db, legacy):
    buyer = user(db)
    city_seat = seat(db)
    order = pay_seat(db, city_seat, buyer)
    if legacy:
        order.order_type = OrderType.SELF_OPERATED_ORDER
        db.commit()
    message = 'ordinary refunds' if legacy else '城市合伙人订单不支持退款'
    with pytest.raises(ConflictError, match=message):
        OrderService._validate_paid_refund_transition(db, order)
    with pytest.raises(ConflictError, match=message):
        OrderService._cancel_order_instance(db, order, refunded=True)
    assert order.pay_status == PayStatus.PAID
    assert serialize_order(db, order)['can_refund'] is False


def test_stale_quote_payment_is_recorded_but_cannot_be_refunded(db):
    buyer = user(db)
    city_seat = seat(db)
    order = Seats.create_purchase_order(db, city_seat.id, buyer, city_seat.price_version)
    city_seat.price_version += 1
    db.commit()
    OrderService._mark_paid(db, order, external_paid_amount=D('1000'))
    assert order.pay_status == PayStatus.PAID
    assert db.get(CityPartnerPurchase, order.id).settlement_error
    assert db.query(CityPartnerRotationFlow).count() == 0
    assert summary(db, system_account(db, 'COMPANY').id).available_amount == D('0')
    serialized = serialize_order(db, order, include_detail=True)
    assert serialized['can_refund'] is False
    assert serialized['status_text'] == '席位未取得，待平台处理'
    assert '申请退款' not in serialized['payment_message']
    with pytest.raises(ConflictError, match='城市合伙人订单不支持退款'):
        OrderService._cancel_order_instance(db, order, refunded=True)
    assert order.pay_status == PayStatus.PAID


def test_pending_quote_is_reused_and_only_first_payment_acquires_seat(db):
    first, second = user(db), user(db)
    city_seat = seat(db)
    order = Seats.create_purchase_order(db, city_seat.id, first, 0)
    assert Seats.create_purchase_order(db, city_seat.id, first, 0).id == order.id
    other = Seats.create_purchase_order(db, city_seat.id, second, 0)
    OrderService._mark_paid(db, order)
    OrderService._mark_paid(db, other)
    assert city_seat.current_user_id == first.id
    assert db.query(CityPartnerRotationFlow).count() == 1
    assert db.get(CityPartnerPurchase, other.id).settlement_error
    assert other.pay_status == PayStatus.PAID


def test_capped_seat_is_not_sold_again(db):
    buyer = user(db)
    city_seat = seat(db, price_cap=D('1000'))
    pay_seat(db, city_seat, buyer)
    assert Seats.serialize_seat(db, city_seat)['purchasable'] is False
    with pytest.raises(ConflictError, match='price cap'):
        Seats.create_purchase_order(db, city_seat.id, user(db), city_seat.price_version)


def test_rules_round_trip_reads_persisted_values(db):
    buyer = user(db)
    product, config, _ = product_order(db, buyer)
    snapshot = ProductService._zone_config_snapshot(db, product)
    assert snapshot['city_partner_commission_enabled'] is True
    assert snapshot['city_partner_amount'] == 100.0
    assert snapshot['city_partner_direct_reward_amount'] == 400.0
    assert snapshot['city_partner_commission_rule_version'] == config.city_partner_commission_rule_version


@pytest.mark.parametrize(
    'changes',
    [
        {'city_partner_amount': -1},
        {'city_partner_upline_decay_rate': -1},
        {'city_partner_upline_decay_rate': 101},
        {'city_partner_upline_max_levels': 0},
        {'city_partner_upline_max_levels': 8},
        {'city_partner_remainder_account': 'USER'},
    ],
)
def test_schema_rejects_invalid_rules(changes):
    with pytest.raises(ValidationError):
        ProductZoneConfigUpdateRequest(**changes)


def test_rule_pool_validation_does_not_depend_on_existing_beneficiaries(db):
    buyer = user(db)
    product, config, _ = product_order(db, buyer)
    values = ProductZoneConfigUpdateRequest(city_partner_commission_enabled=True, city_partner_amount=901).model_dump()
    with pytest.raises(ConflictError, match='profit pool'):
        ProductService._validate_zone_config_payload(product, values)
    with pytest.raises(ConflictError, match='profit pool'):
        validate_city_partner_rule(config, 800, 700)


def test_seven_levels_are_rounded_per_unit_and_company_tail_settles_and_reverses(db):
    ancestors = []
    parent = None
    for _ in range(8):
        parent = user(db, parent)
        ancestors.append(parent)
    buyer = user(db, parent)
    holder = user(db)
    city_seat = seat(db)
    city_seat.current_user_id = holder.id
    db.commit()
    _, _, order = product_order(db, buyer, quantity=2)
    OrderService._mark_paid(db, order)
    flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).all()
    assert sum(f.commission_amount for f in flows) == D('1800')
    seventh = next(f for f in flows if f.commission_role == 'UPLINE' and f.level == 7)
    assert seventh.commission_amount == D('6.24')
    company = next(f for f in flows if f.commission_role == 'COMPANY_REMAINDER')
    assert company.commission_amount == D('6.26')
    assert company.beneficiary_user_id == system_account(db, 'COMPANY').id
    order.order_status = OrderStatus.COMPLETED
    db.commit()
    Commissions.settle_for_order(db, order.id)
    assert company.status == CommissionStatus.SETTLED
    assert summary(db, company.beneficiary_user_id).available_amount == D('6.26')
    Commissions.cancel_for_order(db, order.id)
    db.commit()
    assert all(f.status == CommissionStatus.CANCELED for f in flows)
    assert summary(db, company.beneficiary_user_id).available_amount == D('0')


def test_zero_direct_pays_no_uplines_despite_legacy_knobs_and_nonshipping_settles(db):
    grandparent = user(db)
    parent = user(db, grandparent)
    buyer = user(db, parent)
    _, _, order = product_order(
        db,
        buyer,
        shipping=False,
        city_partner_amount=0,
        city_partner_direct_reward_amount=0,
        city_partner_upline_initial_amount=100,
        city_partner_upline_decay_rate=0,
    )
    OrderService._mark_paid(db, order)
    assert order.order_status == OrderStatus.COMPLETED
    assert summary(db, parent.id).available_amount == D('0')
    assert summary(db, grandparent.id).total_amount == D('0')
    assert summary(db, system_account(db, 'COMPANY').id).available_amount == D('900')


def test_city_mode_never_enters_region_reward_calculation(db, monkeypatch):
    buyer = user(db)
    _, _, order = product_order(db, buyer)
    OrderService._mark_paid(db, order)

    def unexpected(*args):
        pytest.fail('Original region reward calculator must not run')

    monkeypatch.setattr(RegionDividendService, '_product_region_rewards', unexpected)
    assert RegionDividendService.process_order_dividend(db, order, {'province': '陕西省', 'city': '西安市'}) == []


def test_new_flows_visible_to_mobile_and_admin_with_team_scope(db):
    parent = user(db)
    buyer = user(db, parent, team_id=77)
    _, _, order = product_order(db, buyer)
    OrderService._mark_paid(db, order)
    mobile = [serialize_commission_flow(f) for f in Commissions.flows(db, parent.id)]
    assert mobile and all(f['commission_mode'] == 'CITY_PARTNER' for f in mobile)
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    visible = Commissions.list_flows_page_for_admin(db, admin)
    assert visible['total'] == 2
    assert any(f['level_label'] == '公司尾差' for f in visible['items'])
    outsider = user(db, role=GlobalRole.TEAM_ADMIN, team_id=88)
    assert Commissions.list_flows_page_for_admin(db, outsider)['total'] == 0
    rules = Commissions.list_product_rules_for_admin(db, admin)
    assert rules['items'][0]['city_partner_amount'] == 100
    assert rules['items'][0]['commission_mode'] == 'CITY_PARTNER'


def test_historical_mode_is_preserved_when_global_mode_changes(db):
    buyer = user(db)
    _, _, order = product_order(db, buyer)
    OrderService._mark_paid(db, order)
    config = db.query(CommissionConfig).first()
    config.commission_mode = CommissionMode.ORIGINAL
    db.commit()
    order.order_status = OrderStatus.COMPLETED
    db.commit()
    Commissions.settle_for_order(db, order.id)
    assert order.commission_mode == CommissionMode.CITY_PARTNER
    assert db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).one().status == CommissionStatus.SETTLED


def test_decimal_validation_error_returns_422_json():
    import asyncio
    import json

    from fastapi import Request
    from fastapi.exceptions import RequestValidationError

    from app.main import validation_error_handler

    with pytest.raises(ValidationError) as caught:
        ProductZoneConfigUpdateRequest(city_partner_direct_reward_amount=-1)
    response = asyncio.run(
        validation_error_handler(Request({'type': 'http'}), RequestValidationError(caught.value.errors()))
    )
    assert response.status_code == 422
    assert json.loads(response.body)['data'][0]['type'] == 'greater_than_equal'


def test_admin_rule_save_roundtrip_has_new_version(db):
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    product, config, _ = product_order(db, admin)
    previous_version = config.city_partner_commission_rule_version
    payload = ProductZoneConfigUpdateRequest(city_partner_commission_enabled=True, city_partner_amount=100).model_dump()
    response = ProductService.update_zone_config_for_admin(db, product.id, admin, payload)
    assert response['city_partner_amount'] == 100
    assert response['city_partner_commission_enabled'] is True
    assert response['city_partner_commission_rule_version'] != previous_version


def test_invalid_persisted_rule_prevents_enabling_new_mode(db):
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    _, rule, _ = product_order(db, admin)
    config = db.query(CommissionConfig).first()
    config.commission_mode = CommissionMode.ORIGINAL
    rule.city_partner_amount = D('10000')
    db.commit()
    with pytest.raises(ConflictError, match='profit pool'):
        Commissions.update_commission_mode(db, CommissionMode.CITY_PARTNER, admin.id)
    assert config.commission_mode == CommissionMode.ORIGINAL


def test_internal_account_initialization_is_idempotent(db):
    company = system_account(db, 'COMPANY')
    summary(db, company.id).available_amount = D('17')
    db.commit()
    ensure_system_accounts(db)
    db.commit()
    assert system_account(db, 'COMPANY').id == company.id
    assert summary(db, company.id).available_amount == D('17')


def test_paid_seat_order_cannot_settle_while_provider_refund_is_processing(db):
    from app.models.enums import PaymentChannel, PaymentStatus, RefundStatus
    from app.models.payment import PaymentRefund, PaymentTransaction
    buyer = user(db)
    city_seat = seat(db)
    order = Seats.create_purchase_order(db, city_seat.id, buyer, 0)
    order.pay_status = PayStatus.PAID
    order.order_status = OrderStatus.PENDING_SHIP
    order.paid_amount = D('1000')
    tx = PaymentTransaction(order_id=order.id, order_no=order.order_no, channel=PaymentChannel.WECHAT,
                            status=PaymentStatus.PAID, currency='CNY', amount=D('1000'), out_trade_no='SEAT-PAY')
    db.add(tx)
    db.flush()
    db.add(PaymentRefund(order_id=order.id, payment_transaction_id=tx.id, order_no=order.order_no,
                          channel=PaymentChannel.WECHAT, status=RefundStatus.PROCESSING, currency='CNY',
                          original_amount=D('1000'), refund_amount=D('1000'), out_refund_no='SEAT-REFUND'))
    db.commit()
    with pytest.raises(ConflictError, match='refund is processing'):
        Seats.purchase_or_rotate(db, city_seat.id, buyer, order.id)
    assert db.query(CityPartnerRotationFlow).count() == 0
    assert summary(db, system_account(db, 'COMPANY').id).available_amount == D('0')
