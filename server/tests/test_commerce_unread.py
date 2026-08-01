from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Initialize the API package before importing services, matching the app startup order.
from app.api.v1.mobile_serializers import serialize_footprint as _serialize_footprint  # noqa: F401
from app.services.commerce_service import COMMERCE_VIEW_MARKER_KEYS, CommerceService


def test_unread_counts_only_include_activity_newer_than_view_marker():
    viewed_at = datetime(2026, 8, 1, 10, 0)
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        SimpleNamespace(status_key='commerce_shipping', viewed_at=viewed_at),
        SimpleNamespace(status_key='commerce_footprints', viewed_at=viewed_at),
    ]
    user = SimpleNamespace(id=7)
    shipments = [
        SimpleNamespace(updated_at=viewed_at - timedelta(minutes=1)),
        SimpleNamespace(updated_at=viewed_at + timedelta(minutes=1)),
    ]
    footprints = [
        SimpleNamespace(last_viewed_at=viewed_at + timedelta(minutes=2)),
        SimpleNamespace(last_viewed_at=viewed_at + timedelta(minutes=3)),
    ]

    with (
        patch.object(CommerceService, 'list_shipments', return_value=shipments),
        patch.object(CommerceService, 'list_footprints', return_value=footprints),
    ):
        counts = CommerceService.unread_counts(db, user)

    assert counts == {'shipping': 1, 'footprints': 2}


def test_marking_commerce_views_creates_both_markers():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    user = SimpleNamespace(id=8)

    with patch.object(CommerceService, 'unread_counts', return_value={'shipping': 0, 'footprints': 0}):
        counts = CommerceService.mark_viewed(db, user, 'all')

    assert db.add.call_count == len(COMMERCE_VIEW_MARKER_KEYS)
    assert {call.args[0].status_key for call in db.add.call_args_list} == set(COMMERCE_VIEW_MARKER_KEYS.values())
    assert all(call.args[0].user_id == 8 for call in db.add.call_args_list)
    assert counts == {'shipping': 0, 'footprints': 0}
    db.commit.assert_called_once()
