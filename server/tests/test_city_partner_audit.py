from decimal import Decimal as D

import pytest
from pydantic import ValidationError
from test_city_partner import db as audit_db
from test_city_partner import product_order, seat, user

from app.core.exceptions import ConflictError
from app.models.city_partner import CityPartnerCommissionFlow, CityPartnerPurchase
from app.models.commission import CommissionConfig, CommissionModeSwitchLog
from app.models.commission_audit import CommissionRuleAudit
from app.models.enums import CommissionMode, GlobalRole, PayStatus
from app.schemas.city_partner import CityPartnerSeatCreateRequest
from app.schemas.product import ProductZoneConfigUpdateRequest
from app.services.catalog_service import ProductService
from app.services.city_partner_rules import upline_calculations
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.commission_audit import list_rule_changes
from app.services.commission_service import CommissionService as Commissions
from app.services.order_service import OrderService
from app.utils.helpers import now

db = audit_db


def test_seat_rule_history_invalidates_quotes_and_keeps_actor_and_prior_values(db):
    admin, buyer = user(db), user(db)
    city_seat = Seats.create_seat(db, '陕西省', '西安市', D('1000'), D('20'), operator_id=admin.id)
    quoted = Seats.create_purchase_order(db, city_seat.id, buyer, 0)
    Seats.update_seat(db, city_seat.id, D('25'), None, 'ACTIVE', operator_id=admin.id, change_reason='调整增长率')
    history = list_rule_changes(db, 'SEAT', city_seat.id)
    assert history['total'] == 2
    change = history['items'][0]
    assert change['operator_id'] == admin.id and change['reason'] == '调整增长率'
    assert D(change['before_values']['price_growth_rate']) == D('20')
    assert D(change['after_values']['price_growth_rate']) == D('25')
    assert history['items'][1]['rule_version'] != change['rule_version']
    OrderService._mark_paid(db, quoted)
    assert quoted.pay_status == PayStatus.PAID
    assert db.get(CityPartnerPurchase, quoted.id).settlement_error
    assert city_seat.current_user_id is None


def test_product_rule_history_retains_each_version_without_paid_orders(db):
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    product, _, _ = product_order(db, admin)
    for amount, reason in [(50, '第一次'), (75, '第二次')]:
        payload = ProductZoneConfigUpdateRequest(city_partner_commission_enabled=True, city_partner_amount=amount,
                                                  change_reason=reason).model_dump()
        ProductService.update_zone_config_for_admin(db, product.id, admin, payload)
    changes = list_rule_changes(db, 'PRODUCT', product.id)['items']
    assert len(changes) == 2 and changes[0]['rule_version'] != changes[1]['rule_version']
    assert D(changes[0]['before_values']['city_partner_amount']) == D('50')
    assert D(changes[0]['after_values']['city_partner_amount']) == D('75')
    assert changes[0]['operator_id'] == admin.id and changes[0]['reason'] == '第二次'
    payload = ProductZoneConfigUpdateRequest(city_partner_commission_enabled=True, city_partner_amount=901).model_dump()
    with pytest.raises(ConflictError):
        ProductService.update_zone_config_for_admin(db, product.id, admin, payload)
    assert db.query(CommissionRuleAudit).filter_by(entity_type='PRODUCT').count() == 2


def test_mode_readiness_requires_rules_and_active_seats_but_not_a_holder(db):
    admin = user(db)
    readiness = Commissions.mode_readiness(db)
    assert not readiness['ready']
    assert {c['key'] for c in readiness['checks'] if not c['passed']} == {'products', 'cities'}
    product_order(db, admin)
    city_seat = seat(db)
    assert city_seat.current_user_id is None
    assert Commissions.mode_readiness(db)['ready']
    Seats.update_seat(db, city_seat.id, D('20'), None, 'INACTIVE')
    assert not Commissions.mode_readiness(db)['ready']


def test_last_switch_metadata_does_not_use_later_withdraw_config_timestamp(db):
    admin = user(db)
    Commissions.update_commission_mode(db, CommissionMode.ORIGINAL, admin.id, '切换原因')
    log = db.query(CommissionModeSwitchLog).one()
    expected = log.switched_at
    config = db.query(CommissionConfig).first()
    config.updated_at = now()
    config.updated_by = user(db).id
    db.commit()
    status = Commissions.commission_mode(db)
    assert status['reason'] == '切换原因'
    assert status['operator_id'] == admin.id
    assert status['switched_at'].startswith(expected.isoformat())


@pytest.mark.parametrize('province,city', [('陕西省', '西安市'), ('北京市', '北京市')])
def test_city_picker_accepts_same_standard_as_shipping_addresses(province, city):
    payload = CityPartnerSeatCreateRequest(province=province, city=city, initial_price=1000)
    assert payload.city == city


def test_city_picker_rejects_mismatched_or_invented_city():
    with pytest.raises(ValidationError, match='标准'):
        CityPartnerSeatCreateRequest(province='陕西省', city='不存在的城市', initial_price=1000)


def test_raw_upline_keeps_fractional_cents_and_per_piece_rounding():
    values = {'city_partner_direct_reward_amount': 400, 'city_partner_upline_max_levels': 7,
              'city_partner_upline_decay_rate': 50}
    assert upline_calculations(values, 2)[-1] == (D('6.250000'), D('6.24'))


def test_legacy_flow_does_not_claim_recovered_calculation_precision(db):
    buyer = user(db)
    _, _, order = product_order(db, buyer)
    OrderService._mark_paid(db, order)
    flow = db.query(CityPartnerCommissionFlow).one()
    flow.calculation_precision_known = False
    db.commit()
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    assert Commissions.list_flows_page_for_admin(db, admin)['items'][0]['calculated_amount'] is None


def test_price_edit_creates_audit_version_and_preserves_paid_snapshot(db):
    from app.models.product import ProductCategory
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    product, rule, order = product_order(db, admin)
    product.owner_id = admin.id
    db.commit()
    OrderService._mark_paid(db, order)
    original_version = rule.city_partner_commission_rule_version
    category = ProductCategory(name='验收分类', slug='audit-price')
    db.add(category)
    db.commit()
    ProductService.update_for_admin(db, product.id, admin, {
        'product_name': product.product_name, 'product_type': product.product_type,
        'zone_type': product.zone_type, 'owner_type': product.owner_type,
        'category_id': category.id, 'sale_price': D('1700'), 'cost_price': D('700'),
        'stock': product.stock, 'requires_shipping': True,
    })
    change = list_rule_changes(db, 'PRODUCT', product.id)['items'][0]
    assert D(change['before_values']['_sale_price']) == D('1600')
    assert D(change['after_values']['_sale_price']) == D('1700')
    assert change['rule_version'] != original_version
    assert change['operator_id'] == admin.id
    assert order.sale_price_snapshot == D('1600')
