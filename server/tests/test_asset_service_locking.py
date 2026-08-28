from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.enums import AssetType
from app.services.asset_service import AssetService


def test_refund_consumed_amount_locks_and_refreshes_asset_account():
    account = SimpleNamespace(
        available_amount=Decimal('10.00'),
        consumed_amount=Decimal('5.00'),
        updated_at=None,
    )
    db = MagicMock()

    with patch.object(AssetService, 'ensure_user_asset_accounts', return_value=False):
        filtered_query = db.query.return_value.filter.return_value
        locked_query = filtered_query.populate_existing.return_value.with_for_update.return_value
        locked_query.first.return_value = account

        result = AssetService.refund_consumed_amount(
            db,
            user_id=42,
            asset_type=AssetType.BALANCE,
            amount=Decimal('3.00'),
            business_type='ORDER_CANCEL_REFUND',
            source_id=7,
            source_no='ORDER-7',
        )

    assert result is account
    assert account.available_amount == Decimal('13.00')
    assert account.consumed_amount == Decimal('2.00')
    filtered_query.populate_existing.assert_called_once_with()
    filtered_query.populate_existing.return_value.with_for_update.assert_called_once_with()
    ledger = db.add.call_args.args[0]
    assert ledger.before_amount == Decimal('10.00')
    assert ledger.after_amount == Decimal('13.00')
