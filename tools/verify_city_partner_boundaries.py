"""Characterize current financial boundaries, not approval of draft policy choices.

Run from server with PYTHONPATH containing server and server/tests.
All database cases use isolated SQLite, without changing running application data.
"""
from decimal import Decimal as D, ROUND_DOWN

import pytest

from test_city_partner import db, user, seat, pay_seat, product_order, summary
from app.core.exceptions import ConflictError
from app.models.city_partner import CityPartnerCommissionFlow, CityPartnerRotationFlow
from app.models.commission import CommissionConfig, CommissionFlow
from app.models.enums import CommissionMode, CommissionStatus, OrderStatus, PayStatus, GlobalRole, PaymentChannel, PaymentStatus
from app.models.product import ProductCategory
from app.models.payment import PaymentTransaction
from app.services.catalog_service import ProductService
from app.services.payment_service import PaymentService
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.city_partner_rules import upline_amounts
from app.services.commission_service import CommissionService as Commissions
from app.services.order_service import OrderService


def test_original_mode_blocks_new_seat_purchase(db):
    db.query(CommissionConfig).first().commission_mode = CommissionMode.ORIGINAL
    db.commit()
    buyer, city = user(db), seat(db)
    with pytest.raises(ConflictError, match='暂未开放'):
        pay_seat(db, city, buyer)
    assert city.current_user_id is None
    assert db.query(CommissionConfig).first().commission_mode == CommissionMode.ORIGINAL


def test_holder_cannot_replace_self_but_can_buy_another_city(db):
    buyer, city = user(db), seat(db)
    pay_seat(db, city, buyer)
    with pytest.raises(ConflictError, match='cannot replace themselves'):
        pay_seat(db, city, buyer)
    assert db.query(CityPartnerRotationFlow).count() == 1
    other = seat(db, city='咸阳市')
    pay_seat(db, other, buyer)
    assert city.current_user_id == other.current_user_id == buyer.id


def test_growth_edit_leaves_incoming_quote_unchanged(db):
    city = seat(db)
    pay_seat(db, city, user(db))
    Seats.update_seat(db, city.id, D('50'), None, 'ACTIVE')
    assert city.current_price == D('1200')
    order = pay_seat(db, city, user(db))
    assert order.paid_amount == D('1200')
    assert city.current_price == D('1800')


def test_zero_growth_then_positive_growth_reopens_seat(db):
    city = seat(db)
    Seats.update_seat(db, city.id, D('0'), None, 'ACTIVE')
    pay_seat(db, city, user(db))
    Seats.update_seat(db, city.id, D('20'), None, 'ACTIVE')
    assert city.current_price == D('1200')
    assert pay_seat(db, city, user(db)).order_status == OrderStatus.COMPLETED


def test_raising_cap_after_cap_sale_reopens_seat(db):
    city = seat(db, price_cap=D('1100'))
    pay_seat(db, city, user(db))
    pay_seat(db, city, user(db))
    Seats.update_seat(db, city.id, D('20'), D('2000'), 'ACTIVE')
    assert city.current_price == D('1320')
    assert pay_seat(db, city, user(db)).order_status == OrderStatus.COMPLETED


def test_direct_parent_does_not_receive_first_upline(db):
    parent = user(db)
    buyer = user(db, parent)
    _, _, order = product_order(db, buyer)
    OrderService._mark_paid(db, order)
    flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id, beneficiary_user_id=parent.id).all()
    assert {f.commission_role for f in flows} == {'DIRECT'}
    assert sum(f.commission_amount for f in flows) == D('400')


def test_disabled_product_generates_neither_mode_flows(db):
    _, _, order = product_order(db, user(db), city_partner_commission_enabled=False)
    OrderService._mark_paid(db, order)
    assert order.commission_mode == CommissionMode.CITY_PARTNER
    assert db.query(CityPartnerCommissionFlow).count() == 0
    assert db.query(CommissionFlow).count() == 0


def test_completed_shipping_order_releases_immediately_and_rejects_refund(db):
    _, _, order = product_order(db, user(db))
    OrderService._mark_paid(db, order)
    flow = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).one()
    assert flow.status == CommissionStatus.FROZEN
    order.order_status = OrderStatus.SHIPPED
    db.commit()
    OrderService._confirm_order_instance(db, order)
    assert flow.status == CommissionStatus.SETTLED
    assert summary(db, flow.beneficiary_user_id).available_amount == D('900')
    with pytest.raises(ConflictError, match='status cannot be refunded'):
        OrderService._validate_paid_refund_transition(db, order)


def test_nonshipping_refund_cannot_reverse_spent_commission(db):
    _, _, order = product_order(db, user(db), shipping=False)
    OrderService._mark_paid(db, order)
    flow = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).one()
    assert flow.status == CommissionStatus.SETTLED
    OrderService._validate_paid_refund_transition(db, order)
    summary(db, flow.beneficiary_user_id).available_amount = D('0')
    db.commit()
    with pytest.raises(ConflictError, match='insufficient for refund'):
        Commissions.cancel_for_order(db, order.id)
    db.rollback()
    assert db.get(type(flow), flow.id).status == CommissionStatus.SETTLED


def test_payment_uses_order_item_sale_but_current_cost(db):
    product, _, order = product_order(db, user(db))
    product.sale_price, product.cost_price = D('2000'), D('600')
    db.commit()
    OrderService._mark_paid(db, order)
    assert order.sale_price_snapshot == D('1600')
    assert order.cost_price_snapshot == D('600')
    assert order.profit_pool_snapshot == D('1000')


def test_asset_deduction_does_not_reduce_commission_pool(db):
    _, _, order = product_order(db, user(db))
    order.discount_amount, order.payable_amount = D('800'), D('800')
    db.commit()
    OrderService._mark_paid(db, order, external_paid_amount=D('800'))
    assert order.paid_amount == D('1600')
    assert order.profit_pool_snapshot == D('900')


def test_pending_order_retains_payment_after_valid_repricing(db):
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    product, _, order = product_order(db, admin)
    product.owner_id = admin.id
    category = ProductCategory(name='边界验证', slug='boundary-reprice')
    db.add(category)
    db.commit()
    # Existing new-mode allocation is valid against new 2000 - 1000 pricing,
    # but exceeds the pending order's old sale price minus the new cost.
    ProductService.update_for_admin(db, product.id, admin, {
        'product_name': product.product_name, 'product_type': product.product_type,
        'zone_type': product.zone_type, 'owner_type': product.owner_type,
        'category_id': category.id, 'sale_price': D('2000'), 'cost_price': D('1000'),
        'stock': product.stock, 'requires_shipping': True,
    })
    tx = PaymentTransaction(order_id=order.id, order_no=order.order_no,
                            channel=PaymentChannel.WECHAT, amount=D('1600'),
                            out_trade_no='boundary-pending-payment')
    db.add(tx)
    db.commit()
    PaymentService.confirm_paid_order(db, tx, provider_trade_no='boundary-provider-success')
    assert db.get(type(order), order.id).pay_status == PayStatus.PAID
    assert db.get(PaymentTransaction, tx.id).status == PaymentStatus.PAID
    assert 'exceeds product profit pool' in Commissions.settlement_failure(order)
    assert order.profit_pool_snapshot == D('600')
    assert order.order_status == OrderStatus.PENDING_SHIP
    assert db.query(CityPartnerCommissionFlow).count() == 0


def test_nonshipping_checkout_has_no_city_and_city_share_goes_to_company(db):
    buyer = user(db)
    city = seat(db)
    pay_seat(db, city, user(db))
    _, _, order = product_order(db, buyer, shipping=False)
    order.legacy_address_id = OrderService._validate_address(db, buyer.id, order.legacy_address_id, False)
    db.commit()
    OrderService._mark_paid(db, order)
    flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).all()
    assert order.city_partner_user_id is None
    assert order.city is None
    assert [(f.commission_role, f.commission_amount) for f in flows] == [('COMPANY_REMAINDER', D('900'))]


def test_legacy_independent_knobs_do_not_override_fixed_halving(db):
    actual = upline_amounts({'city_partner_direct_reward_amount': D('400'), 'city_partner_upline_initial_amount': D('999'),
                            'city_partner_upline_decay_rate': D('33'),
                            'city_partner_upline_max_levels': 7})
    assert actual == [D(x) for x in ('200', '100', '50', '25', '12.50', '6.25', '3.12')]
