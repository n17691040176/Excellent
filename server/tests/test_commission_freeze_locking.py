from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import app.main  # noqa: F401 - initialize application modules in production order
from app.models.commission import CommissionFlow, UserCommission
from app.models.enums import CommissionStatus
from app.models.user import User
from app.services.commission_service import CommissionService


def _locked_queries(db: MagicMock, commission: UserCommission | SimpleNamespace | None):
    user_query = MagicMock()
    user_filtered = user_query.filter.return_value
    user_filtered.with_for_update.return_value.scalar.return_value = 30

    commission_query = MagicMock()
    commission_filtered = commission_query.filter.return_value
    refreshed_query = commission_filtered.populate_existing.return_value
    refreshed_query.with_for_update.return_value.first.return_value = commission

    db.query.side_effect = [user_query, commission_query]
    return user_filtered, commission_filtered, refreshed_query


def _add_frozen_flow(db: MagicMock) -> None:
    CommissionService._add_frozen_flow(
        db,
        order=SimpleNamespace(id=10),
        buyer=SimpleNamespace(id=20, team_id=40),
        beneficiary=SimpleNamespace(id=30),
        level=1,
        rate=Decimal('0.10'),
        base_amount=Decimal('20.00'),
    )


def test_add_frozen_flow_locks_and_refreshes_existing_commission_account():
    commission = SimpleNamespace(
        frozen_amount=Decimal('5.00'),
        total_amount=Decimal('8.00'),
        updated_at=None,
    )
    db = MagicMock()
    user_filtered, commission_filtered, refreshed_query = _locked_queries(db, commission)

    _add_frozen_flow(db)

    assert db.query.call_args_list == [call(User.id), call(UserCommission)]
    user_filtered.with_for_update.assert_called_once_with()
    commission_filtered.populate_existing.assert_called_once_with()
    refreshed_query.with_for_update.assert_called_once_with()
    assert commission.frozen_amount == Decimal('7.00')
    assert commission.total_amount == Decimal('10.00')
    flow = db.add.call_args.args[0]
    assert isinstance(flow, CommissionFlow)
    assert flow.commission_amount == Decimal('2.00')
    assert flow.status == CommissionStatus.FROZEN
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_add_frozen_flow_creates_commission_account_while_user_row_is_locked():
    db = MagicMock()
    user_filtered, commission_filtered, refreshed_query = _locked_queries(db, None)

    def apply_insert_defaults() -> None:
        commission = db.add.call_args_list[0].args[0]
        commission.frozen_amount = Decimal('0.00')
        commission.total_amount = Decimal('0.00')

    db.flush.side_effect = apply_insert_defaults

    _add_frozen_flow(db)

    user_filtered.with_for_update.assert_called_once_with()
    commission_filtered.populate_existing.assert_called_once_with()
    refreshed_query.with_for_update.assert_called_once_with()
    assert db.add.call_count == 2
    commission, flow = (item.args[0] for item in db.add.call_args_list)
    assert isinstance(commission, UserCommission)
    assert commission.user_id == 30
    assert commission.frozen_amount == Decimal('2.00')
    assert commission.total_amount == Decimal('2.00')
    assert isinstance(flow, CommissionFlow)
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
