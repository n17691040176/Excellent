from decimal import Decimal as D

import pytest
from test_city_partner import db as shared_db
from test_city_partner import product_order, user

from app.api.v1.mobile_serializers import serialize_admin_order, serialize_commission_flow
from app.models.commission import CommissionConfig
from app.models.enums import CommissionMode, GlobalRole, MemberLevel, OrderStatus, OrderType, PayStatus
from app.models.order import Order
from app.models.team import Team
from app.services.commission_service import CommissionService
from app.services.order_commission_display import order_commission_fields
from app.services.order_service import OrderService
from app.utils.helpers import now

# Re-export the shared pytest fixture without shadowing an unused import.
db = shared_db


def make_order(db, buyer, **changes):
    values = {'order_no': f'display-{db.query(Order).count()}', 'user_id': buyer.id, 'team_id': buyer.team_id,
              'order_type': OrderType.SELF_OPERATED_ORDER, 'total_amount': D('100'), 'payable_amount': D('100')}
    values.update(changes)
    order = Order(**values)
    db.add(order)
    db.commit()
    return order


@pytest.mark.parametrize('changes, mode, label, version', [
    ({}, 'UNLOCKED', '待锁定', None),
    ({'commission_mode': CommissionMode.CITY_PARTNER}, 'UNLOCKED', '待锁定', None),
    ({'order_status': OrderStatus.REFUND}, 'UNLOCKED', '未锁定', None),
    ({'pay_status': PayStatus.PAID}, 'ORIGINAL', '原分润', 'legacy'),
    ({'pay_status': PayStatus.REFUNDED, 'order_status': OrderStatus.REFUND,
      'commission_mode': CommissionMode.CITY_PARTNER, 'commission_rule_version': 'city-saved'}, 'CITY_PARTNER', '新分润', 'city-saved'),
    ({'paid_at': now()}, 'ORIGINAL', '原分润', 'legacy'),
    ({'mode_locked_at': now(), 'commission_mode': CommissionMode.CITY_PARTNER}, 'CITY_PARTNER', '新分润', 'legacy'),
    ({'order_type': OrderType.CITY_PARTNER_ORDER, 'commission_mode': CommissionMode.CITY_PARTNER,
      'commission_rule_version': 'seat-quote-v2'}, 'CITY_PARTNER', '新分润', 'seat-quote-v2'),
])
def test_admin_mode_display_and_filter_agree_for_pending_paid_refunded_and_legacy(db, changes, mode, label, version):
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    order = make_order(db, admin, **changes)
    # The current global mode must never relabel an existing order.
    for global_mode in [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER]:
        db.query(CommissionConfig).first().commission_mode = global_mode
        db.commit()
        for detailed in [False, True]:
            result = serialize_admin_order(db, order, include_detail=detailed)
            assert (result['commission_mode'], result['commission_mode_text'], result['commission_rule_version']) == (mode, label, version)
        for candidate in ['ORIGINAL', 'CITY_PARTNER', 'UNLOCKED']:
            result = OrderService.list_orders_for_admin(db, admin, commission_mode=candidate)
            assert result['total'] == (1 if candidate == mode else 0)


def test_mode_filters_combine_with_type_status_pagination_and_team_scope(db):
    admin = user(db, role=GlobalRole.SUPER_ADMIN)
    team = Team(name='display-team', owner_user_id=admin.id)
    db.add(team)
    db.commit()
    team_admin = user(db, role=GlobalRole.TEAM_ADMIN, team_id=team.id)
    buyer = user(db, team_id=team.id)
    new_orders = [make_order(db, buyer, pay_status=PayStatus.PAID, order_status=OrderStatus.COMPLETED,
                            commission_mode=CommissionMode.CITY_PARTNER) for _ in range(3)]
    make_order(db, buyer, order_type=OrderType.CITY_PARTNER_ORDER, commission_mode=CommissionMode.CITY_PARTNER)
    make_order(db, buyer, pay_status=PayStatus.PAID)  # Original paid order.
    make_order(db, buyer)  # Unpaid default ORIGINAL must not enter the original filter.
    make_order(db, admin, pay_status=PayStatus.PAID, commission_mode=CommissionMode.CITY_PARTNER)
    for page in [1, 2, 3]:
        result = OrderService.list_orders_for_admin(db, team_admin, commission_mode='CITY_PARTNER',
                    order_type='SELF_OPERATED_ORDER', order_status='COMPLETED', page_size=1, page=page)
        assert result['total'] == 3
        assert [row.id for row in result['items']] == [new_orders[-page].id]
    assert OrderService.list_orders_for_admin(db, team_admin, commission_mode='ORIGINAL')['total'] == 1
    assert OrderService.list_orders_for_admin(db, team_admin, commission_mode='UNLOCKED')['total'] == 1
    assert OrderService.list_orders_for_admin(db, admin, commission_mode='CITY_PARTNER')['total'] == 5


def test_payment_locks_current_mode_and_later_switch_preserves_display(db):
    buyer = user(db)
    _, _, order = product_order(db, buyer)
    assert order_commission_fields(order)['commission_mode'] == 'UNLOCKED'
    OrderService._mark_paid(db, order, external_paid_amount=order.total_amount)
    snapshot = order_commission_fields(order)
    assert snapshot['commission_mode'] == 'CITY_PARTNER' and snapshot['mode_locked_at']
    db.query(CommissionConfig).first().commission_mode = CommissionMode.ORIGINAL
    db.commit()
    assert order_commission_fields(order) == snapshot


def test_mobile_commission_records_keep_their_own_modes_after_switch(db):
    parent = user(db)
    parent.member_level = MemberLevel.DEALER
    db.commit()
    buyer = user(db, parent=parent)
    config = db.query(CommissionConfig).first()
    for mode in [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER]:
        config.commission_mode = mode
        db.commit()
        _, rule, order = product_order(db, buyer)
        rule.custom_commission_enabled = True
        rule.custom_commission_method = 'FIXED_AMOUNT'
        rule.custom_commission_level2_enabled = True
        rule.custom_commission_level2_amount = D('8')
        db.commit()
        OrderService._mark_paid(db, order, external_paid_amount=order.total_amount)
    config.commission_mode = CommissionMode.ORIGINAL
    db.commit()
    rows = [serialize_commission_flow(flow) for flow in CommissionService.flows(db, parent.id)]
    assert {(row['commission_mode'], row['commission_mode_text']) for row in rows} == {
        ('ORIGINAL', '原分润'), ('CITY_PARTNER', '新分润')}
