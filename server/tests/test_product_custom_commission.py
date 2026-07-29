from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import app.main  # noqa: F401 - initialize application modules in production order
from app.core.exceptions import ConflictError
from app.models.enums import OrderType, ZoneType
from app.services.catalog_service import ProductService
from app.services.commission_service import CommissionService


def custom_config(method: str = 'RATE') -> SimpleNamespace:
    return SimpleNamespace(
        custom_commission_method=method,
        custom_commission_level1_rate=Decimal('12.50'),
        custom_commission_level2_rate=Decimal('5.00'),
        custom_commission_level3_rate=Decimal('0.00'),
        custom_commission_level1_amount=Decimal('8.00'),
        custom_commission_level2_amount=Decimal('3.00'),
        custom_commission_level3_amount=Decimal('0.00'),
    )


def zone_payload(**overrides) -> dict:
    payload = {
        'custom_commission_enabled': True,
        'custom_commission_method': 'RATE',
        'custom_commission_level1_rate': 12.5,
        'custom_commission_level2_rate': 5,
        'custom_commission_level3_rate': 0,
        'custom_commission_level1_amount': 0,
        'custom_commission_level2_amount': 0,
        'custom_commission_level3_amount': 0,
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
    def test_rate_value_is_converted_from_percentage(self):
        rate, amount = CommissionService._custom_commission_value(custom_config(), 1, Decimal('3'))

        self.assertEqual(rate, Decimal('0.125'))
        self.assertIsNone(amount)

    def test_fixed_amount_is_calculated_per_item_quantity(self):
        rate, amount = CommissionService._custom_commission_value(
            custom_config('FIXED_AMOUNT'),
            1,
            Decimal('3'),
        )

        self.assertEqual(rate, Decimal('0'))
        self.assertEqual(amount, Decimal('24.00'))

    def test_custom_rule_does_not_read_generic_distribution_rule(self):
        db = MagicMock()
        order = SimpleNamespace(id=10)
        buyer = SimpleNamespace(id=20)
        beneficiary = SimpleNamespace(id=30)
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
            custom_commission_level3_amount=0,
        )

        with self.assertRaisesRegex(ConflictError, 'At least one custom commission value'):
            ProductService._validate_zone_config_payload(product, payload)

    def test_custom_rate_total_cannot_exceed_one_hundred_percent(self):
        product = SimpleNamespace(zone_type=ZoneType.SELF_OPERATED)
        payload = zone_payload(
            custom_commission_level1_rate=60,
            custom_commission_level2_rate=30,
            custom_commission_level3_rate=20,
        )

        with self.assertRaisesRegex(ConflictError, 'total rate cannot exceed 100'):
            ProductService._validate_zone_config_payload(product, payload)
