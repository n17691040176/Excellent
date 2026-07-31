from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.asset import UserAssetLedger
from app.models.enums import MemberLevel
from app.models.region_agent import RegionAgent
from app.models.region_dividend import RegionDividendFlow
from app.models.user import User
from app.services.region_dividend_service import RegionDividendService


def test_member_levels_are_the_only_four_supported_levels():
    assert list(MemberLevel) == [
        MemberLevel.NORMAL_MEMBER,
        MemberLevel.DEALER,
        MemberLevel.COUNTY_AGENT,
        MemberLevel.CITY_AGENT,
    ]
    assert [level.label for level in MemberLevel] == ['普通会员', '经销商', '区代理', '市代理']


def test_region_agent_admin_update_keeps_assignment_active_and_syncs_member_level():
    db = MagicMock()
    agent = SimpleNamespace(
        id=11,
        user_id=21,
        agent_type='COUNTY_AGENT',
        province='浙江省',
        city='杭州市',
        district='西湖区',
        status='APPROVED',
        agreement_signed=True,
        effective_at=None,
        expired_at=None,
        dividend_rate=1,
        audited_by=None,
        audited_at=None,
        audit_remark=None,
    )
    user = SimpleNamespace(id=21, member_level=MemberLevel.DEALER)

    def get_model(model, record_id):
        if model is RegionAgent and record_id == agent.id:
            return agent
        if model is User and record_id == user.id:
            return user
        return None

    db.get.side_effect = get_model
    area_query = MagicMock()
    area_query.filter.return_value.first.return_value = None
    area_query.filter.return_value.filter.return_value.first.return_value = None
    duplicate_query = MagicMock()
    duplicate_query.filter.return_value.first.return_value = None
    active_query = MagicMock()
    active_query.filter.return_value.all.return_value = [SimpleNamespace(agent_type='CITY_AGENT')]
    db.query.side_effect = [area_query, duplicate_query, active_query]

    result = RegionDividendService.update_agent(
        db,
        agent.id,
        admin_user_id=1,
        agent_type='CITY_AGENT',
        province='浙江省',
        city='杭州市',
        district='',
        dividend_rate=0.75,
    )

    assert result is agent
    assert agent.status == 'APPROVED'
    assert agent.agreement_signed is True
    assert agent.agent_type == 'CITY_AGENT'
    assert agent.district == ''
    assert agent.dividend_rate == 0.75
    assert user.member_level == MemberLevel.CITY_AGENT
    db.commit.assert_called_once()


def test_public_region_agent_application_route_is_removed():
    from app.api.v1 import api_router

    paths = {route.path for route in api_router.routes}
    assert '/api/v1/region-agents/apply' not in paths


def test_allocate_region_reward_credits_balance_and_records_exact_percentage():
    db = MagicMock()
    duplicate_query = MagicMock()
    duplicate_query.filter.return_value.first.return_value = None
    account_query = MagicMock()
    account = SimpleNamespace(
        available_amount=Decimal('10.00'),
        total_amount=Decimal('30.00'),
        updated_at=None,
    )
    account_query.filter.return_value.with_for_update.return_value.first.return_value = account
    db.query.side_effect = [duplicate_query, account_query]

    order = SimpleNamespace(id=101, order_no='OD101')
    agent = SimpleNamespace(
        id=9,
        user_id=88,
        agent_type='COUNTY_AGENT',
        dividend_rate=1.5,
        total_orders=2,
        total_dividend=3.0,
    )

    flow = RegionDividendService._allocate_reward(
        db,
        order,
        agent,
        Decimal('200.00'),
        '浙江省',
        '杭州市',
        '西湖区',
    )

    assert isinstance(flow, RegionDividendFlow)
    assert Decimal(str(flow.dividend_rate)) == Decimal('1.5')
    assert Decimal(str(flow.dividend_amount)) == Decimal('3.00')
    assert account.available_amount == Decimal('13.00')
    assert account.total_amount == Decimal('33.00')
    assert agent.total_orders == 3
    assert Decimal(str(agent.total_dividend)) == Decimal('6.0')
    ledgers = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], UserAssetLedger)]
    assert len(ledgers) == 1
    assert ledgers[0].before_amount == Decimal('10.00')
    assert ledgers[0].after_amount == Decimal('13.00')


def test_allocate_region_reward_is_idempotent_for_order_and_agent():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = (1,)
    order = SimpleNamespace(id=101, order_no='OD101')
    agent = SimpleNamespace(
        id=9,
        user_id=88,
        agent_type='CITY_AGENT',
        dividend_rate=0.5,
        total_orders=1,
        total_dividend=1.0,
    )

    result = RegionDividendService._allocate_reward(
        db, order, agent, Decimal('200.00'), '浙江省', '杭州市', ''
    )

    assert result is None
    db.add.assert_not_called()
