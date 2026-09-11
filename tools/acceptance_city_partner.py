"""Selected draft-document acceptance cases; this is not full-document coverage.

From server (PowerShell):
  $env:PYTHONPATH = "$PWD;$PWD/tests"
  python -m pytest ../tools/acceptance_city_partner.py -q --tb=short

Uses isolated SQLite and the existing real-ORM fixture. No production data.
The initial run had three failures; the follow-up implementation closes them.
See docs/acceptance_20260910_city_partner.md for the historical evidence.
"""
from copy import deepcopy
from decimal import Decimal as D

import pytest

from test_city_partner import db as document_db, pay_seat, product_order, seat, summary, user
from app.core.exceptions import ConflictError
from app.models.address import UserAddress
from app.models.asset import UserAssetAccount
from app.models.city_partner import CityPartnerCommissionFlow, CityPartnerRotationFlow, CityPartnerSeat
from app.models.commission import CommissionConfig, CommissionFlow, CommissionModeSwitchLog
from app.models.enums import AssetType, CommissionMode, CommissionStatus, MemberLevel, OrderStatus
from app.models.region_agent import RegionAgent
from app.models.region_dividend import RegionDividendFlow
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.commission_service import CommissionService as Commissions
from app.services.order_service import OrderService

db = document_db


def seven_level_order(db, quantity=1):
    parent = None
    for _ in range(8):
        parent = user(db, parent)
    buyer = user(db, parent)
    holder = user(db)
    city_seat = seat(db)
    city_seat.current_user_id = holder.id
    db.commit()
    product, rules, order = product_order(db, buyer, quantity=quantity)
    OrderService._mark_paid(db, order)
    return product, rules, order, city_seat


@pytest.mark.parametrize('quantity', [1, 2])
def test_doc_6_3_and_6_6_exact_example_and_per_piece_rounding(db, quantity):
    _, _, order, _ = seven_level_order(db, quantity)
    flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).all()
    expected = {
        ('CITY_PARTNER', None): D('100'), ('DIRECT', 0): D('400'),
        ('UPLINE', 1): D('200'), ('UPLINE', 2): D('100'), ('UPLINE', 3): D('50'),
        ('UPLINE', 4): D('25'), ('UPLINE', 5): D('12.50'),
        ('UPLINE', 6): D('6.25'), ('UPLINE', 7): D('3.12'),
        ('COMPANY_REMAINDER', None): D('3.13'),
    }
    assert {(f.commission_role, f.level): f.commission_amount for f in flows} == {
        key: value * quantity for key, value in expected.items()
    }
    assert sum(f.commission_amount for f in flows) == order.profit_pool_snapshot == D('900') * quantity
    assert order.sale_price_snapshot == D('1600') * quantity
    assert order.cost_price_snapshot == D('700') * quantity
    assert db.query(CommissionFlow).filter_by(order_id=order.id).count() == 0
    assert db.query(RegionDividendFlow).filter_by(order_id=order.id).count() == 0


@pytest.mark.parametrize('depth,expected_remainder', [(0, '900'), (1, '500'), (3, '200')])
def test_doc_6_4_missing_beneficiaries_go_to_company(db, depth, expected_remainder):
    parent = None
    for _ in range(depth):
        parent = user(db, parent)
    buyer = user(db, parent)
    _, _, order = product_order(db, buyer)
    OrderService._mark_paid(db, order)
    flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).all()
    company = next(f for f in flows if f.commission_role == 'COMPANY_REMAINDER')
    assert company.commission_amount == D(expected_remainder)
    assert not any(f.commission_role == 'CITY_PARTNER' for f in flows)
    assert len([f for f in flows if f.commission_role == 'UPLINE']) == max(0, depth - 1)
    assert sum(f.commission_amount for f in flows) == D('900')


def test_doc_4_2_and_7_paid_snapshot_survives_rule_city_and_mode_changes(db):
    product, rules, order, city_seat = seven_level_order(db)
    snapshot = deepcopy(order.city_partner_rule_snapshot)
    holder_id, version = order.city_partner_user_id, order.commission_rule_version
    product.sale_price, product.cost_price = D('9999'), D('9998')
    rules.city_partner_amount = D('0')
    rules.city_partner_commission_rule_version = 'edited-after-payment'
    city_seat.current_user_id = user(db).id
    db.get(UserAddress, order.legacy_address_id).city = '咸阳市'
    db.query(CommissionConfig).first().commission_mode = CommissionMode.ORIGINAL
    db.commit()
    OrderService._mark_paid(db, order)
    order.order_status = OrderStatus.COMPLETED
    db.commit()
    Commissions.settle_for_order(db, order.id)
    assert order.city_partner_rule_snapshot == snapshot
    assert order.city_partner_user_id == holder_id
    assert order.city == '西安市'
    assert order.commission_rule_version == version
    assert order.profit_pool_snapshot == D('900')
    flows = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).all()
    assert len(flows) == 10
    assert all(f.status == CommissionStatus.SETTLED for f in flows)
    Commissions.cancel_for_order(db, order.id)
    db.commit()
    assert all(f.status == CommissionStatus.CANCELED for f in flows)
    assert all(summary(db, f.beneficiary_user_id).available_amount == 0 for f in flows)


def test_doc_4_2_unpaid_order_locks_mode_at_payment(db):
    buyer = user(db)
    _, _, order = product_order(db, buyer)
    config = db.query(CommissionConfig).first()
    config.commission_mode = CommissionMode.ORIGINAL
    db.commit()
    OrderService._mark_paid(db, order)
    assert order.commission_mode == CommissionMode.ORIGINAL
    assert order.mode_locked_at is not None
    assert db.query(CityPartnerCommissionFlow).count() == 0


def test_doc_13_original_commissions_and_agents_survive_mode_switch_and_refund(db):
    parent = user(db)
    parent.member_level = MemberLevel.DEALER
    buyer = user(db, parent)
    _, rule, order = product_order(db, buyer, shipping=False)
    rule.custom_commission_enabled = True
    rule.custom_commission_method = 'FIXED_AMOUNT'
    rule.custom_commission_level2_enabled = True
    rule.custom_commission_level2_amount = D('8')
    agents = []
    for role, member, district, amount in [
        ('CITY_AGENT', MemberLevel.CITY_AGENT, '', '5'),
        ('COUNTY_AGENT', MemberLevel.COUNTY_AGENT, '雁塔区', '3'),
    ]:
        beneficiary = user(db)
        beneficiary.member_level = member
        db.add(RegionAgent(user_id=beneficiary.id, province='陕西省', city='西安市', district=district,
                           agent_type=role, status='APPROVED', agreement_signed=True))
        setattr(rule, f'custom_commission_{role.lower()}_enabled', True)
        setattr(rule, f'custom_commission_{role.lower()}_amount', D(amount))
        agents.append((beneficiary.id, D(amount)))
    config = db.query(CommissionConfig).first()
    config.commission_mode = CommissionMode.ORIGINAL
    db.commit()
    OrderService._mark_paid(db, order)
    assert summary(db, parent.id).available_amount == D('8')
    assert db.query(RegionDividendFlow).filter_by(order_id=order.id).count() == 2
    for uid, amount in agents:
        assert db.query(UserAssetAccount).filter_by(user_id=uid, asset_type=AssetType.BALANCE).one().available_amount == amount
    config.commission_mode = CommissionMode.CITY_PARTNER
    db.commit()
    OrderService._mark_paid(db, order)
    assert db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).count() == 0
    assert summary(db, parent.id).available_amount == D('8')
    OrderService._validate_paid_refund_transition(db, order)
    OrderService._cancel_order_instance(db, order, refunded=True)
    assert summary(db, parent.id).available_amount == 0
    for uid, _ in agents:
        assert db.query(UserAssetAccount).filter_by(user_id=uid, asset_type=AssetType.BALANCE).one().available_amount == 0


def test_doc_5_3_and_5_4_cap_uses_actual_appreciation_and_replaces_holder(db):
    previous, parent = user(db), user(db)
    incoming = user(db, parent)
    city_seat = seat(db, price_cap=D('1100'))
    first = pay_seat(db, city_seat, previous)
    assert city_seat.current_price == D('1100')
    second = pay_seat(db, city_seat, incoming)
    flow = db.query(CityPartnerRotationFlow).filter_by(order_id=second.id).one()
    assert [flow.principal_refund_amount, flow.appreciation_reward_amount, flow.company_amount,
            flow.parent_reward_amount, flow.operations_amount] == [D('1000'), D('40'), D('30'), D('10'), D('20')]
    assert city_seat.current_user_id == incoming.id
    assert city_seat.current_order_id == second.id
    assert db.query(CityPartnerRotationFlow).filter_by(order_id=first.id).count() == 1


def test_doc_5_1_duplicate_city_seat_is_rejected(db):
    seat(db)
    with pytest.raises(ConflictError):
        seat(db)


def test_doc_11_unpaid_seat_does_not_transfer_ownership(db):
    buyer, city_seat = user(db), seat(db)
    order = Seats.create_purchase_order(db, city_seat.id, buyer, 0)
    with pytest.raises(ConflictError):
        Seats.purchase_or_rotate(db, city_seat.id, buyer, order.id)
    assert city_seat.current_user_id is None
    assert db.query(CityPartnerRotationFlow).count() == 0


def test_doc_4_3_mode_switch_persists_audit(db):
    admin = user(db)
    before = Commissions.commission_mode(db)
    Commissions.update_commission_mode(db, CommissionMode.ORIGINAL, admin.id, 'document acceptance')
    log = db.query(CommissionModeSwitchLog).one()
    assert log.from_mode == CommissionMode.CITY_PARTNER
    assert log.to_mode == CommissionMode.ORIGINAL
    assert log.operator_id == admin.id and log.reason == 'document acceptance'
    assert log.switched_at is not None
    assert log.pending_order_count == before['pending_order_count']
    assert log.frozen_commission_amount == D(str(before['frozen_commission_amount']))


def test_doc_4_3_switch_requires_city_configuration(db):
    admin = user(db)
    product_order(db, admin)
    config = db.query(CommissionConfig).first()
    config.commission_mode = CommissionMode.ORIGINAL
    db.commit()
    assert db.query(CityPartnerSeat).count() == 0
    with pytest.raises(ConflictError, match='(?i)city|seat|config'):
        Commissions.update_commission_mode(db, CommissionMode.CITY_PARTNER, admin.id, 'no cities configured')


def test_doc_10_1_mode_status_exposes_last_switch_reason(db):
    admin = user(db)
    Commissions.update_commission_mode(db, CommissionMode.ORIGINAL, admin.id, 'document acceptance')
    status = Commissions.commission_mode(db)
    assert status.get('reason') == 'document acceptance', status


def test_doc_9_2_flow_preserves_unrounded_calculation(db):
    _, _, order, _ = seven_level_order(db)
    seventh = db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id, commission_role='UPLINE', level=7).one()
    assert seventh.commission_amount == D('3.12')
    assert seventh.calculated_amount == D('3.125'), 'Original amount must retain the discarded fractional cent'
