from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import app.main  # noqa: F401 - initialize application modules in production order
from app.core.exceptions import ConflictError
from app.models.enums import CommissionStatus, MemberLevel, OrderType, ZoneType
from app.services.catalog_service import ProductService
from app.services.commission_service import CommissionService


def custom_config(method: str = 'RATE') -> SimpleNamespace:
    return SimpleNamespace(
        custom_commission_method=method,
        custom_commission_level1_enabled=True,
        custom_commission_level2_enabled=True,
        custom_commission_county_agent_enabled=True,
        custom_commission_city_agent_enabled=False,
        custom_commission_level1_rate=Decimal('12.50'),
        custom_commission_level2_rate=Decimal('5.00'),
        custom_commission_county_agent_rate=Decimal('2.00'),
        custom_commission_city_agent_rate=Decimal('0.00'),
        custom_commission_level1_amount=Decimal('8.00'),
        custom_commission_level2_amount=Decimal('3.00'),
        custom_commission_county_agent_amount=Decimal('2.00'),
        custom_commission_city_agent_amount=Decimal('0.00'),
    )


def zone_payload(**overrides) -> dict:
    payload = {
        'custom_commission_enabled': True,
        'custom_commission_method': 'RATE',
        'custom_commission_level1_enabled': True,
        'custom_commission_level2_enabled': True,
        'custom_commission_county_agent_enabled': False,
        'custom_commission_city_agent_enabled': False,
        'custom_commission_level1_rate': 12.5,
        'custom_commission_level2_rate': 5,
        'custom_commission_county_agent_rate': 0,
        'custom_commission_city_agent_rate': 0,
        'custom_commission_level1_amount': 0,
        'custom_commission_level2_amount': 0,
        'custom_commission_county_agent_amount': 0,
        'custom_commission_city_agent_amount': 0,
        'points_only_enabled': False,
        'points_cash_enabled': True,
        'cash_only_enabled': True,
        'balance_purchase_enabled': True,
        'balance_only_enabled': True,
        'balance_points_enabled': True,
    }
    payload.update(overrides)
    return payload


class ProductCustomCommissionTest(TestCase):
    def test_normal_member_rate_is_converted_from_percentage(self):
        rate, amount = CommissionService._custom_commission_value(
            custom_config(),
            MemberLevel.NORMAL_MEMBER,
            Decimal('3'),
        )

        self.assertEqual(rate, Decimal('0.125'))
        self.assertIsNone(amount)

    def test_dealer_fixed_amount_is_calculated_per_item_quantity(self):
        rate, amount = CommissionService._custom_commission_value(
            custom_config('FIXED_AMOUNT'),
            MemberLevel.DEALER,
            Decimal('3'),
        )

        self.assertEqual(rate, Decimal('0'))
        self.assertEqual(amount, Decimal('9.00'))

    def test_region_agents_are_not_paid_again_through_referral_commission(self):
        rate, amount = CommissionService._custom_commission_value(
            custom_config(),
            MemberLevel.COUNTY_AGENT,
            Decimal('1'),
        )

        self.assertEqual(rate, Decimal('0'))
        self.assertIsNone(amount)

    def test_custom_rule_does_not_read_generic_distribution_rule(self):
        db = MagicMock()
        order = SimpleNamespace(id=10)
        buyer = SimpleNamespace(id=20)
        beneficiary = SimpleNamespace(id=30, member_level=MemberLevel.NORMAL_MEMBER)
        config = custom_config('FIXED_AMOUNT')

        with (
            patch.object(CommissionService, '_ancestor_users', return_value=[(1, beneficiary)]),
            patch.object(CommissionService, '_distribution_enabled', return_value=True),
            patch('app.services.commission_service.EarningRuleService.rate_for_commission_level') as generic_rate,
            patch.object(CommissionService, '_add_frozen_flow') as add_flow,
        ):
            CommissionService._freeze_distribution_rewards(
                db,
                order,
                buyer,
                [(100, Decimal('40.00'), Decimal('2'))],
                {100: config},
            )

        generic_rate.assert_not_called()
        self.assertEqual(add_flow.call_args.kwargs['commission_amount'], Decimal('16.00'))

    def test_custom_rule_rewards_only_nearest_eligible_user_for_each_member_level(self):
        db = MagicMock()
        order = SimpleNamespace(id=10)
        buyer = SimpleNamespace(id=20)
        nearest_normal = SimpleNamespace(id=30, member_level=MemberLevel.NORMAL_MEMBER)
        farther_normal = SimpleNamespace(id=31, member_level=MemberLevel.NORMAL_MEMBER)

        with (
            patch.object(
                CommissionService,
                '_ancestor_users',
                return_value=[(1, nearest_normal), (2, farther_normal)],
            ),
            patch.object(CommissionService, '_distribution_enabled', return_value=True),
            patch.object(CommissionService, '_add_frozen_flow') as add_flow,
        ):
            CommissionService._freeze_distribution_rewards(
                db,
                order,
                buyer,
                [(100, Decimal('40.00'), Decimal('1'))],
                {100: custom_config()},
            )

        add_flow.assert_called_once()
        self.assertIs(add_flow.call_args.args[3], nearest_normal)

    def test_first_referrer_uses_dealer_rule_when_their_member_level_is_dealer(self):
        db = MagicMock()
        order = SimpleNamespace(id=10)
        buyer = SimpleNamespace(id=20)
        dealer = SimpleNamespace(id=30, member_level=MemberLevel.DEALER)

        with (
            patch.object(CommissionService, '_ancestor_users', return_value=[(1, dealer)]),
            patch.object(CommissionService, '_distribution_enabled', return_value=True),
            patch.object(CommissionService, '_add_frozen_flow') as add_flow,
        ):
            CommissionService._freeze_distribution_rewards(
                db,
                order,
                buyer,
                [(100, Decimal('40.00'), Decimal('2'))],
                {100: custom_config('FIXED_AMOUNT')},
            )

        self.assertEqual(add_flow.call_args.kwargs['commission_amount'], Decimal('6.00'))

    def test_custom_product_profit_is_excluded_from_team_reward(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        order = SimpleNamespace(id=10, order_type=OrderType.NORMAL_PRODUCT)
        buyer = SimpleNamespace(id=20)
        custom_item = (100, Decimal('40.00'), Decimal('1'))
        standard_item = (200, Decimal('60.00'), Decimal('1'))

        with (
            patch.object(CommissionService, '_order_profit_items', return_value=[custom_item, standard_item]),
            patch.object(CommissionService, '_custom_commission_configs', return_value={100: custom_config()}),
            patch.object(CommissionService, '_freeze_distribution_rewards'),
            patch.object(CommissionService, '_freeze_direct_team_reward') as team_reward,
        ):
            CommissionService.freeze_for_order(db, order, buyer)

        self.assertEqual(team_reward.call_args.args[-1], [standard_item])

    def test_selected_fixed_method_requires_a_fixed_amount(self):
        product = SimpleNamespace(zone_type=ZoneType.SELF_OPERATED)
        payload = zone_payload(
            custom_commission_method='FIXED_AMOUNT',
            custom_commission_level1_amount=0,
            custom_commission_level2_amount=0,
            custom_commission_county_agent_amount=0,
            custom_commission_city_agent_amount=0,
        )

        with self.assertRaisesRegex(ConflictError, 'At least one custom commission value'):
            ProductService._validate_zone_config_payload(product, payload)

    def test_custom_rate_total_cannot_exceed_one_hundred_percent(self):
        product = SimpleNamespace(zone_type=ZoneType.SELF_OPERATED)
        payload = zone_payload(
            custom_commission_level1_rate=60,
            custom_commission_level2_rate=30,
            custom_commission_county_agent_enabled=True,
            custom_commission_county_agent_rate=20,
        )

        with self.assertRaisesRegex(ConflictError, 'total rate cannot exceed 100'):
            ProductService._validate_zone_config_payload(product, payload)

    def test_admin_product_rule_exposes_all_member_level_configurations(self):
        product = SimpleNamespace(id=100, product_name='测试商品', zone_type=ZoneType.SELF_OPERATED)
        config = custom_config()
        config.updated_at = None

        data = CommissionService.serialize_product_rule(product, config)

        self.assertEqual(data['product_name'], '测试商品')
        self.assertEqual(data['method'], 'RATE')
        self.assertTrue(data['level1_enabled'])
        self.assertTrue(data['level2_enabled'])
        self.assertTrue(data['county_agent_enabled'])
        self.assertFalse(data['city_agent_enabled'])
        self.assertEqual(data['level1_rate'], 12.5)
        self.assertEqual(data['level2_rate'], 5.0)
        self.assertEqual(data['county_agent_rate'], 2.0)
        self.assertEqual(data['city_agent_rate'], 0.0)

    def test_admin_commission_flow_contains_users_order_and_level_label(self):
        flow = SimpleNamespace(
            id=1,
            beneficiary_user_id=10,
            source_user_id=20,
            order_id=30,
            level=2,
            rate=Decimal('5.00'),
            base_amount=Decimal('40.00'),
            commission_amount=Decimal('2.00'),
            status=CommissionStatus.SETTLED,
            settled_at=None,
            created_at=None,
        )
        beneficiary = SimpleNamespace(nickname='受益人', phone='13800000000')
        source = SimpleNamespace(nickname='购买人', phone='13900000000')
        order = SimpleNamespace(order_no='OD30')

        data = CommissionService.serialize_admin_flow(flow, beneficiary, source, order)

        self.assertEqual(data['order_no'], 'OD30')
        self.assertEqual(data['beneficiary_nickname'], '受益人')
        self.assertEqual(data['source_nickname'], '购买人')
        self.assertEqual(data['level_label'], '2级分润')
        self.assertEqual(data['status'], 'SETTLED')
