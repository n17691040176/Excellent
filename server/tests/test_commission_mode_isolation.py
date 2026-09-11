"""Business assertions for mode isolation and the confirmed fixed seven-layer policy."""
from copy import deepcopy
from decimal import Decimal as D

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from test_city_partner import db as shared_db
from test_city_partner import pay_seat, product_order, seat, summary, user

from app.api.v1.products import update_admin_zone_config
from app.core.exceptions import ConflictError
from app.models.asset import UserAssetAccount
from app.models.city_partner import CityPartnerCommissionFlow, CityPartnerPurchase, CityPartnerRotationFlow
from app.models.commission import CommissionConfig, CommissionFlow, UserCommission
from app.models.earning_rule import EarningRule
from app.models.enums import (
    CommissionMode,
    CommissionStatus,
    GlobalRole,
    MemberLevel,
    OrderStatus,
    OrderType,
    PayStatus,
)
from app.models.order import Order, OrderItem
from app.models.region_agent import RegionAgent
from app.models.region_dividend import RegionDividendFlow
from app.schemas.product import ProductZoneConfigUpdateRequest
from app.services.city_partner_rules import upline_calculations
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.commission_service import CommissionService as Commissions
from app.services.order_service import OrderService
from app.services.region_dividend_service import RegionDividendService as Regions
from app.utils.helpers import now

# Re-export the shared pytest fixture without shadowing an unused import.
db = shared_db


def make_scenario(db, method='FIXED_AMOUNT', quantity=1, shipping=True, repurchase=False, depth=8):
    parent = None
    for _ in range(depth):
        parent = user(db, parent)
        parent.member_level = MemberLevel.DEALER
    if parent and method != 'GENERIC':
        parent.member_level = MemberLevel.NORMAL_MEMBER
        db.add(Order(order_no=f'QUALIFY-{parent.id}', user_id=parent.id, order_type=OrderType.SELF_OPERATED_ORDER,
                     total_amount=D('1'), payable_amount=D('0'), paid_amount=D('1'),
                     pay_status=PayStatus.PAID, order_status=OrderStatus.COMPLETED))
    buyer = user(db, parent)
    holder = user(db)
    city = seat(db)
    city.current_user_id = holder.id
    product, rule, order = product_order(db, buyer, quantity=quantity, shipping=shipping)
    if repurchase:
        order.order_type = OrderType.REPURCHASE_ORDER
    rule.custom_commission_enabled = method != 'GENERIC'
    rule.custom_commission_method = 'RATE' if method == 'RATE' else 'FIXED_AMOUNT'
    for role, amount, rate in [('level1', '8', '12.5'), ('level2', '3', '5'),
                               ('city_agent', '5', '3'), ('county_agent', '3', '2')]:
        setattr(rule, f'custom_commission_{role}_enabled', True)
        setattr(rule, f'custom_commission_{role}_amount', D(amount))
        setattr(rule, f'custom_commission_{role}_rate', D(rate))
    for kind, member, district in [('CITY_AGENT', MemberLevel.CITY_AGENT, ''), ('COUNTY_AGENT', MemberLevel.COUNTY_AGENT, '雁塔区')]:
        agent = user(db)
        agent.member_level = member
        db.add(RegionAgent(user_id=agent.id, province='陕西省', city='西安市', district=district,
                           agent_type=kind, status='APPROVED', agreement_signed=True))
    if method == 'GENERIC':
        for level, rate in [(1, '10'), (2, '5'), (3, '2')]:
            for event in ('ORDER_COMPLETE', 'REPEAT_PURCHASE'):
                db.add(EarningRule(rule_code=f'GENERIC-{event}-{level}', rule_name='baseline rule', rule_type='DIRECT_REWARD',
                                   commission_level=level, trigger_event=event, calculation_basis='PROFIT',
                                   calculation_method='RATE', reward_rate=D(rate), is_active=True))
        db.add(EarningRule(rule_code='GENERIC-TEAM', rule_name='team rule', rule_type='TEAM_REWARD',
                           member_level='DEALER', trigger_event='ORDER_COMPLETE', calculation_basis='PROFIT',
                           calculation_method='RATE', reward_rate=D('3'), is_active=True))
    db.commit()
    return buyer, product, rule, order, city


def ledger_state(db):
    return {
        'commissions': [(r.user_id, r.frozen_amount, r.available_amount, r.total_amount)
                        for r in db.query(UserCommission).order_by(UserCommission.user_id)],
        'assets': [(r.user_id, r.asset_type, r.available_amount, r.total_amount)
                   for r in db.query(UserAssetAccount).order_by(UserAssetAccount.user_id)],
        'old_flows': [(r.order_id, r.beneficiary_user_id, r.level, r.commission_amount, r.status)
                      for r in db.query(CommissionFlow).order_by(CommissionFlow.id)],
        'region_flows': [(r.order_id, r.agent_user_id, r.dividend_amount, r.status)
                         for r in db.query(RegionDividendFlow).order_by(RegionDividendFlow.id)],
    }


@pytest.mark.parametrize('mode', [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER])
@pytest.mark.parametrize('method', ['FIXED_AMOUNT', 'RATE', 'GENERIC'])
@pytest.mark.parametrize('lifecycle', ['complete', 'refund_frozen', 'refund_settled'])
def test_switch_at_payment_and_lifecycle_never_mixes_modes(db, mode, method, lifecycle):
    buyer, product, rule, order, city = make_scenario(db, method, quantity=2, shipping=lifecycle != 'refund_settled')
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    opposite = CommissionMode.CITY_PARTNER if mode == CommissionMode.ORIGINAL else CommissionMode.ORIGINAL
    # This order already exists: switching now must affect its first payment.
    Commissions.update_commission_mode(db, mode, admin.id, 'payment mode')
    OrderService._mark_paid(db, order)
    locked_version, locked_time = order.commission_rule_version, order.mode_locked_at
    snapshot = deepcopy(order.city_partner_rule_snapshot)
    for selected in (opposite, mode, opposite):
        Commissions.update_commission_mode(db, selected, admin.id, 'isolation regression')
    OrderService._mark_paid(db, order)
    assert order.commission_mode == mode
    assert order.commission_rule_version == locked_version and order.mode_locked_at == locked_time
    assert order.city_partner_rule_snapshot == snapshot

    if lifecycle == 'complete':
        order.order_status = OrderStatus.SHIPPED
        db.commit()
        OrderService._confirm_order_instance(db, order)
        before = ledger_state(db)
        OrderService._mark_paid(db, order)
        OrderService._confirm_order_instance(db, order)
        assert ledger_state(db) == before
    if mode == CommissionMode.CITY_PARTNER:
        assert db.query(CommissionFlow).filter_by(order_id=order.id).count() == 0
        assert db.query(RegionDividendFlow).filter_by(order_id=order.id).count() == 0
        flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).all()
        assert len(flows) == 10 and sum(f.commission_amount for f in flows) == D('1800')
        direct = next(f for f in flows if f.commission_role == 'DIRECT')
        first = next(f for f in flows if f.commission_role == 'UPLINE' and f.level == 1)
        assert direct.beneficiary_user_id == buyer.parent_id
        assert first.beneficiary_user_id != direct.beneficiary_user_id
        assert direct.commission_amount == D('800') and first.commission_amount == D('400')
    else:
        assert db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).count() == 0
        expected = {'FIXED_AMOUNT': D('22'), 'RATE': D('315'), 'GENERIC': D('360')}[method]
        assert sum(f.commission_amount for f in db.query(CommissionFlow).filter_by(order_id=order.id)) == expected
        region = list(db.query(RegionDividendFlow).filter_by(order_id=order.id))
        if lifecycle != 'refund_frozen':
            assert sum(f.dividend_amount for f in region) == {'FIXED_AMOUNT': D('16'), 'RATE': D('90'), 'GENERIC': D('0')}[method]
    if lifecycle != 'complete':
        assert OrderService.refund_order_with_result(db, order)['completed']
        before = ledger_state(db)
        assert OrderService.refund_order_with_result(db, order)['completed']
        assert ledger_state(db) == before
        assert all(r.frozen_amount == r.available_amount == 0 for r in db.query(UserCommission))
        assert all(r.available_amount == 0 for r in db.query(UserAssetAccount))


def test_editing_one_mode_does_not_reset_other_mode_through_api(db):
    _, product, rule, _, _ = make_scenario(db)
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    old = {c.name: getattr(rule, c.name) for c in rule.__table__.columns if c.name.startswith('custom_')}
    update_admin_zone_config(product.id, ProductZoneConfigUpdateRequest(city_partner_direct_reward_amount=300), db, admin)
    assert all(getattr(rule, key) == value for key, value in old.items())
    assert rule.city_partner_direct_reward_amount == D('300') and rule.city_partner_amount == D('100')
    assert rule.city_partner_upline_initial_amount == D('150')
    update_admin_zone_config(product.id, ProductZoneConfigUpdateRequest(custom_commission_level1_amount=9), db, admin)
    assert rule.custom_commission_level1_amount == D('9')
    assert rule.city_partner_commission_enabled and rule.city_partner_direct_reward_amount == D('300')


@pytest.mark.parametrize('direct', ['0', '0.01', '1.01', '300', '400.01', '999.99'])
def test_halving_is_derived_and_per_piece_rounding_is_exact(direct):
    amount = D(direct)
    actual = upline_calculations({'city_partner_direct_reward_amount': amount,
                                  'city_partner_upline_initial_amount': 999,
                                  'city_partner_upline_max_levels': 1, 'city_partner_upline_decay_rate': 100}, 3)
    cents = int(amount * 100)
    assert len(actual) == 7
    for index, (raw, issued) in enumerate(actual, 1):
        assert raw == amount / D(2 ** index) * 3
        assert issued == D(cents // (2 ** index)) / 100 * 3


@pytest.mark.parametrize('field,value', [('city_partner_upline_initial_amount', 999), ('city_partner_upline_max_levels', 1), ('city_partner_upline_decay_rate', 100)])
def test_request_cannot_override_derived_upline_fields(field, value):
    with pytest.raises(ValidationError):
        ProductZoneConfigUpdateRequest(**{field: value})


def test_self_replacement_blocked_at_order_and_payment_but_callback_idempotent(db):
    buyer, other = user(db), user(db)
    city = seat(db)
    first = pay_seat(db, city, buyer)
    with pytest.raises(ConflictError, match='cannot replace themselves'):
        Seats.create_purchase_order(db, city.id, buyer, city.price_version)
    Seats.purchase_or_rotate(db, city.id, buyer, first.id)
    assert db.query(CityPartnerRotationFlow).count() == 1
    assert not Seats.serialize_seat(db, city, viewer_id=buyer.id)['purchasable']
    assert Seats.serialize_seat(db, city, viewer_id=other.id)['purchasable']
    # Simulate a historical pending self-purchase created before the new rule.
    pending = Seats.create_purchase_order(db, city.id, other, city.price_version)
    pending.user_id = buyer.id
    db.commit()
    OrderService._mark_paid(db, pending)
    assert pending.pay_status == PayStatus.PAID and city.current_order_id == first.id
    assert 'cannot replace themselves' in db.get(CityPartnerPurchase, pending.id).settlement_error
    with pytest.raises(ConflictError, match='城市合伙人订单不支持退款'):
        OrderService.refund_order_with_result(db, pending)
    assert pending.pay_status == PayStatus.PAID and city.current_order_id == first.id


def test_same_second_switches_have_distinct_audit_versions(db):
    make_scenario(db)
    admin = user(db)
    versions = [Commissions.update_commission_mode(db, mode, admin.id)['rule_version']
                for mode in [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER, CommissionMode.ORIGINAL]]
    assert len(set(versions)) == 3


def test_stale_original_order_cannot_award_region_rewards_after_city_payment(db):
    buyer, _, _, order, _ = make_scenario(db)
    OrderService._mark_paid(db, order)
    order.order_status = OrderStatus.COMPLETED
    db.commit()
    # A stale identity map is reloaded by the service under its order lock.
    order.commission_mode = CommissionMode.ORIGINAL
    assert Regions.process_order_dividend(db, order, {'province': '陕西省', 'city': '西安市', 'district': '雁塔区'}) == []
    assert db.query(RegionDividendFlow).count() == 0


def test_detected_cross_mode_flows_stop_settlement_and_refund_before_money_moves(db):
    buyer, _, _, order, _ = make_scenario(db)
    OrderService._mark_paid(db, order)
    db.add(CommissionFlow(order_id=order.id, beneficiary_user_id=buyer.id, source_user_id=buyer.id,
                          level=1, rate=D('0'), base_amount=D('900'), commission_amount=D('1'),
                          status=CommissionStatus.FROZEN, created_at=now()))
    order.order_status = OrderStatus.COMPLETED
    db.commit()
    before = ledger_state(db)
    for action in (lambda: Commissions.settle_for_order(db, order.id),
                   lambda: OrderService._validate_paid_refund_transition(db, order),
                   lambda: Commissions.freeze_for_order(db, order, buyer)):
        with pytest.raises(ConflictError, match='mode conflicts'):
            action()
        db.rollback()
    assert ledger_state(db) == before


def test_payment_refreshes_cached_mode_before_locking_snapshot(db):
    _, _, _, order, _ = make_scenario(db)
    config = db.query(CommissionConfig).first()
    config.commission_mode = CommissionMode.ORIGINAL
    db.commit()
    db.execute(text("UPDATE commission_configs SET commission_mode='CITY_PARTNER'"))
    db.commit()
    assert config.commission_mode == CommissionMode.ORIGINAL  # deliberately stale identity map
    OrderService._mark_paid(db, order)
    assert order.commission_mode == CommissionMode.CITY_PARTNER
    assert db.query(CommissionFlow).filter_by(order_id=order.id).count() == 0


def test_switch_refreshes_cached_mode_instead_of_returning_false_success(db):
    make_scenario(db)
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    config = db.query(CommissionConfig).first()
    assert config.commission_mode == CommissionMode.CITY_PARTNER
    db.execute(text("UPDATE commission_configs SET commission_mode='ORIGINAL'"))
    db.commit()
    assert config.commission_mode == CommissionMode.CITY_PARTNER
    result = Commissions.update_commission_mode(db, CommissionMode.CITY_PARTNER, admin.id)
    assert result['previous_mode'] == CommissionMode.ORIGINAL
    assert db.execute(text('SELECT commission_mode FROM commission_configs')).scalar_one() == 'CITY_PARTNER'


@pytest.mark.parametrize('mode', [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER])
def test_refund_refreshes_flow_status_changed_by_another_settlement(db, mode):
    buyer, _, _, order, _ = make_scenario(db)
    config = db.query(CommissionConfig).first()
    config.commission_mode = mode
    db.commit()
    OrderService._mark_paid(db, order)
    flow_type = CommissionFlow if mode == CommissionMode.ORIGINAL else CityPartnerCommissionFlow
    cached_flows = db.query(flow_type).filter_by(order_id=order.id).all()
    assert cached_flows and all(f.status == CommissionStatus.FROZEN for f in cached_flows)
    # Simulate another transaction settling after a refund worker cached its flows.
    db.execute(text(f"UPDATE {flow_type.__tablename__} SET status='SETTLED' WHERE order_id=:oid"), {'oid': order.id})
    db.execute(text('UPDATE user_commissions SET available_amount=frozen_amount, frozen_amount=0'))
    db.commit()
    assert all(f.status == CommissionStatus.FROZEN for f in cached_flows)
    Commissions.cancel_for_order(db, order.id)
    db.commit()
    assert all(r.available_amount == r.frozen_amount == r.total_amount == 0 for r in db.query(UserCommission))


def test_seat_edit_refreshes_price_changed_after_loading_seat(db):
    holder = user(db)
    city = seat(db)
    pay_seat(db, city, holder)
    assert city.current_price == D('1200')
    # Another buyer has completed a 1200 purchase, moving the quote to 1440.
    db.execute(text('UPDATE city_partner_seats SET current_price=1440, price_version=price_version+1 WHERE id=:sid'), {'sid': city.id})
    db.commit()
    assert city.current_price == D('1200')
    with pytest.raises(ConflictError, match='below current price'):
        Seats.update_seat(db, city.id, D('20'), D('1300'), 'ACTIVE')


def test_payment_refreshes_product_rule_cost_and_city_holder(db):
    buyer, product, rule, order, city = make_scenario(db)
    successor = user(db)
    db.execute(text('UPDATE products SET cost_price=800 WHERE id=:pid'), {'pid': product.id})
    db.execute(text('UPDATE product_zone_configs SET city_partner_direct_reward_amount=300 WHERE product_id=:pid'), {'pid': product.id})
    db.execute(text('UPDATE city_partner_seats SET current_user_id=:uid WHERE id=:sid'), {'uid': successor.id, 'sid': city.id})
    db.commit()
    assert product.cost_price == D('700') and rule.city_partner_direct_reward_amount == D('400')
    OrderService._mark_paid(db, order)
    assert order.cost_price_snapshot == D('800')
    assert order.city_partner_user_id == successor.id
    direct = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id, commission_role='DIRECT').one()
    assert direct.commission_amount == D('300')


def test_original_payment_refreshes_cached_cost_and_rate(db):
    buyer, product, rule, order, _ = make_scenario(db, method='RATE')
    db.query(CommissionConfig).first().commission_mode = CommissionMode.ORIGINAL
    db.commit()
    db.execute(text('UPDATE products SET cost_price=800 WHERE id=:pid'), {'pid': product.id})
    db.execute(text('UPDATE product_zone_configs SET custom_commission_level1_rate=20 WHERE product_id=:pid'), {'pid': product.id})
    db.commit()
    assert product.cost_price == D('700') and rule.custom_commission_level1_rate == D('12.5')
    OrderService._mark_paid(db, order)
    direct = db.query(CommissionFlow).filter_by(order_id=order.id, beneficiary_user_id=buyer.parent_id).one()
    assert direct.base_amount == D('800') and direct.commission_amount == D('160')


def test_same_person_can_receive_city_and_direct_without_balance_overwrite(db):
    buyer, _, _, order, city = make_scenario(db)
    city.current_user_id = buyer.parent_id
    db.commit()
    OrderService._mark_paid(db, order)
    assert summary(db, buyer.parent_id).frozen_amount == D('500')
    order.order_status = OrderStatus.SHIPPED
    db.commit()
    OrderService._confirm_order_instance(db, order)
    assert summary(db, buyer.parent_id).available_amount == D('500')
    assert summary(db, buyer.parent_id).frozen_amount == 0


def test_changing_new_rules_does_not_recalculate_paid_old_or_new_orders(db):
    buyer, product, rule, old_order, _ = make_scenario(db)
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    Commissions.update_commission_mode(db, CommissionMode.ORIGINAL, admin.id)
    OrderService._mark_paid(db, old_order)
    _, _, new_order = product_order(db, buyer)
    db.query(OrderItem).filter_by(order_id=new_order.id).one().product_id = product.id
    db.commit()
    Commissions.update_commission_mode(db, CommissionMode.CITY_PARTNER, admin.id)
    OrderService._mark_paid(db, new_order)
    snapshot = deepcopy(new_order.city_partner_rule_snapshot)
    frozen = {r.user_id: r.frozen_amount for r in db.query(UserCommission)}
    update_admin_zone_config(product.id, ProductZoneConfigUpdateRequest(city_partner_direct_reward_amount=250), db, admin)
    for order in (old_order, new_order):
        order.order_status = OrderStatus.SHIPPED
        db.commit()
        OrderService._confirm_order_instance(db, order)
    assert new_order.city_partner_rule_snapshot == snapshot
    assert all(r.available_amount == frozen[r.user_id] and r.frozen_amount == 0 for r in db.query(UserCommission))
    # Reversing the original order leaves new-order money intact in shared accounts.
    Commissions.cancel_for_order(db, old_order.id)
    Regions.reverse_order_dividend(db, old_order)
    db.commit()
    assert summary(db, buyer.parent_id).available_amount == D('400')
    assert all(f.status == CommissionStatus.SETTLED for f in db.query(CityPartnerCommissionFlow).filter_by(order_id=new_order.id))
