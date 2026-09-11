from copy import deepcopy
from decimal import Decimal as D

import pytest
from pydantic import ValidationError
from test_city_partner import db as shared_db
from test_city_partner import product_order, user
from test_commission_mode_isolation import ledger_state, make_scenario

from app.api.v1.products import update_admin_zone_config
from app.core.exceptions import ConflictError
from app.models.city_partner import CityPartnerCommissionFlow
from app.models.commission import CommissionConfig, CommissionFlow
from app.models.enums import CommissionMode, GlobalRole, OrderStatus, PayStatus
from app.models.order import OrderItem
from app.schemas.product import ProductZoneConfigUpdateRequest
from app.services.catalog_service import ProductService
from app.services.city_partner_rules import city_partner_rule_values, upline_calculations, validate_city_partner_rule
from app.services.commission_audit import list_rule_changes
from app.services.order_service import OrderService

db = shared_db


@pytest.mark.parametrize('direct', ['0', '0.01', '400'])
@pytest.mark.parametrize('quantity', [1, 3])
def test_manual_seven_levels_are_independent_of_direct(direct, quantity):
    values = {'city_partner_upline_mode': 'MANUAL', 'city_partner_upline_amounts': ['0.20'] * 7,
              'city_partner_direct_reward_amount': direct}
    assert upline_calculations(values, quantity) == [(D('0.20') * quantity,) * 2] * 7
    assert city_partner_rule_values(values)['city_partner_calculation_policy'] == 'MANUAL_7_V1'
    values['city_partner_upline_mode'] = 'AUTO'
    assert upline_calculations(values, quantity) == upline_calculations({'city_partner_direct_reward_amount': direct}, quantity)


@pytest.mark.parametrize('amounts', [[], ['0.2'] * 6, ['0.2'] * 8, ['-0.01'] * 7, ['0.201'] * 7, ['NaN'] * 7, [None] * 7])
def test_invalid_manual_amounts_rejected_at_api_and_service(amounts):
    payload = {'city_partner_upline_mode': 'MANUAL', 'city_partner_upline_amounts': amounts}
    with pytest.raises(ValidationError):
        ProductZoneConfigUpdateRequest(**payload)
    with pytest.raises(ConflictError):
        city_partner_rule_values(payload)


def test_manual_pool_checks_all_seven_levels_and_preserves_auto_default():
    values = {'city_partner_commission_enabled': True, 'city_partner_upline_mode': 'MANUAL',
              'city_partner_upline_amounts': ['0.20'] * 7, 'city_partner_amount': '1', 'city_partner_direct_reward_amount': '2'}
    validate_city_partner_rule(values, D('14.40'), D('10'))
    with pytest.raises(ConflictError, match='profit pool'):
        validate_city_partner_rule(values, D('14.39'), D('10'))
    assert city_partner_rule_values({})['city_partner_upline_mode'] == 'AUTO'
    for mode in ['FUEL', 'manual', '']:
        with pytest.raises(ValidationError):
            ProductZoneConfigUpdateRequest(city_partner_upline_mode=mode)
        with pytest.raises(ConflictError):
            city_partner_rule_values({'city_partner_upline_mode': mode})


def test_save_manual_amounts_reload_audit_and_partial_edits(db):
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    product, rule, _ = product_order(db, admin)
    values = ['0', '0.01', '0.2', '1', '2', '3', '4']
    result = update_admin_zone_config(product.id, ProductZoneConfigUpdateRequest(
        city_partner_upline_mode='MANUAL', city_partner_upline_amounts=values), db, admin)['data']
    version = result['city_partner_commission_rule_version']
    db.expire_all()
    assert rule.city_partner_upline_amounts == ['0.00', '0.01', '0.20', '1.00', '2.00', '3.00', '4.00']
    assert result['city_partner_upline_mode'] == 'MANUAL'
    change = list_rule_changes(db, 'PRODUCT', product.id)['items'][0]
    assert change['after_values']['city_partner_upline_amounts'] == rule.city_partner_upline_amounts
    assert change['before_values']['city_partner_upline_mode'] == 'AUTO'
    update_admin_zone_config(product.id, ProductZoneConfigUpdateRequest(custom_commission_level1_amount=9), db, admin)
    assert rule.city_partner_upline_mode == 'MANUAL' and rule.city_partner_upline_amounts == result['city_partner_upline_amounts']
    update_admin_zone_config(product.id, ProductZoneConfigUpdateRequest(city_partner_upline_mode='AUTO'), db, admin)
    assert rule.city_partner_commission_rule_version != version
    assert upline_calculations(rule)[0][1] == D('200')
    assert rule.city_partner_upline_amounts == result['city_partner_upline_amounts']
    with pytest.raises(ConflictError, match='profit pool'):
        update_admin_zone_config(product.id, ProductZoneConfigUpdateRequest(
            city_partner_upline_mode='MANUAL', city_partner_upline_amounts=['100'] * 7), db, admin)
    db.rollback()
    assert ProductService.get_zone_config_for_admin(db, product.id, admin)['city_partner_upline_mode'] == 'AUTO'


def test_mixed_products_use_their_own_rule_and_refund_after_switch(db):
    parent = None
    for _ in range(8):
        parent = user(db, parent)
    buyer = user(db, parent)
    fuel, fuel_rule, order = product_order(db, buyer, quantity=3, shipping=False,
        city_partner_upline_mode='MANUAL', city_partner_upline_amounts=['0.20'] * 7,
        city_partner_amount=D('0'), city_partner_direct_reward_amount=D('0'))
    _, normal_rule, extra_order = product_order(db, buyer, shipping=False)
    extra = db.query(OrderItem).filter_by(order_id=extra_order.id).one()
    extra.order_id = order.id
    order.total_amount += extra_order.total_amount
    order.payable_amount = order.total_amount
    db.commit()
    OrderService._mark_paid(db, order)
    flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).all()
    fuel_flows = [f for f in flows if f.product_id == fuel.id and f.commission_role == 'UPLINE']
    assert len(fuel_flows) == 7
    # SQLite NUMERIC uses floating point; exact decimal persistence is checked in MySQL.
    assert all(f.commission_amount == f.calculated_amount.quantize(D('0.01')) == D('0.60') for f in fuel_flows)
    normal = sorted([f for f in flows if f.product_id != fuel.id and f.commission_role == 'UPLINE'], key=lambda f: f.level)
    assert [f.commission_amount for f in normal] == [D(v) for v in ['200', '100', '50', '25', '12.5', '6.25', '3.12']]
    assert sum(f.commission_amount for f in flows) == order.profit_pool_snapshot
    snapshot = deepcopy(order.city_partner_rule_snapshot)
    fuel_rule.city_partner_upline_mode = 'AUTO'
    normal_rule.city_partner_upline_mode = 'MANUAL'
    normal_rule.city_partner_upline_amounts = ['0.20'] * 7
    db.query(CommissionConfig).first().commission_mode = CommissionMode.ORIGINAL
    db.commit()
    OrderService._mark_paid(db, order)
    assert order.city_partner_rule_snapshot == snapshot
    assert snapshot['items'][0]['rule']['city_partner_upline_mode'] == 'MANUAL'
    assert db.query(CommissionFlow).filter_by(order_id=order.id).count() == 0
    OrderService.refund_order_with_result(db, order)
    assert order.pay_status == PayStatus.REFUNDED
    assert order.city_partner_rule_snapshot == snapshot


@pytest.mark.parametrize('depth', [0, 1, 3, 8])
def test_only_existing_uplines_receive_manual_rewards(db, depth):
    buyer, _, rule, order, _ = make_scenario(db, depth=depth)
    rule.city_partner_upline_mode = 'MANUAL'
    rule.city_partner_upline_amounts = ['0.20'] * 7
    db.commit()
    OrderService._mark_paid(db, order)
    flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).all()
    uplines = [f for f in flows if f.commission_role == 'UPLINE']
    assert len(uplines) == max(0, depth - 1)
    assert all(f.commission_amount == D('0.20') for f in uplines)
    assert sum(f.commission_amount for f in flows) == order.profit_pool_snapshot


def test_manual_settings_do_not_affect_original_commission(db):
    buyer, _, rule, order, _ = make_scenario(db)
    rule.city_partner_upline_mode = 'MANUAL'
    rule.city_partner_upline_amounts = ['0.20'] * 7
    db.query(CommissionConfig).first().commission_mode = CommissionMode.ORIGINAL
    db.commit()
    OrderService._mark_paid(db, order)
    before = ledger_state(db)
    assert before['old_flows'] and db.query(CityPartnerCommissionFlow).count() == 0
    rule.city_partner_upline_amounts = ['50'] * 7
    db.query(CommissionConfig).first().commission_mode = CommissionMode.CITY_PARTNER
    db.commit()
    OrderService._mark_paid(db, order)
    assert ledger_state(db) == before
    order.order_status = OrderStatus.SHIPPED
    db.commit()
    OrderService._confirm_order_instance(db, order)
    assert db.query(CityPartnerCommissionFlow).count() == 0
