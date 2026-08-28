from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import app.main  # noqa: F401 - initialize application modules in production order
from app.models.enums import AssetType
from app.services.asset_service import AssetService
from app.services.order_service import OrderService


def _order() -> SimpleNamespace:
    return SimpleNamespace(id=19, user_id=7, order_no='ORDER-19')


def test_refund_deductions_lock_asset_accounts_in_a_stable_order():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        SimpleNamespace(id=4, asset_type='VOUCHER', deduct_amount=Decimal('1.00')),
        SimpleNamespace(id=2, asset_type='POINTS', deduct_amount=Decimal('2.00')),
        SimpleNamespace(id=3, asset_type='BALANCE', deduct_amount=Decimal('3.00')),
    ]

    with patch.object(AssetService, 'refund_consumed_amount') as refund:
        OrderService._refund_order_deductions(db, _order())

    assert [call.args[2] for call in refund.call_args_list] == [
        AssetType.BALANCE,
        AssetType.POINTS,
        AssetType.VOUCHER,
    ]


def test_reward_revocation_locks_multi_user_asset_accounts_in_a_stable_order():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        SimpleNamespace(
            id=8,
            user_id=22,
            asset_type=AssetType.POINTS,
            change_amount=Decimal('1.00'),
        ),
        SimpleNamespace(
            id=3,
            user_id=6,
            asset_type=AssetType.VOUCHER,
            change_amount=Decimal('2.00'),
        ),
        SimpleNamespace(
            id=4,
            user_id=6,
            asset_type=AssetType.BALANCE,
            change_amount=Decimal('3.00'),
        ),
    ]

    with patch.object(AssetService, 'revoke_added_amount') as revoke:
        OrderService._revoke_order_rewards(db, _order())

    assert [(call.args[1], call.args[2]) for call in revoke.call_args_list] == [
        (6, AssetType.BALANCE),
        (6, AssetType.VOUCHER),
        (22, AssetType.POINTS),
    ]
