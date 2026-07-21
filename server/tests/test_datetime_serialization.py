from datetime import UTC, datetime, timedelta, timezone
from unittest import TestCase

from app.api.v1.mobile_serializers import iso_datetime


class DateTimeSerializationTest(TestCase):
    def test_naive_database_datetime_is_serialized_as_utc(self):
        self.assertEqual(
            iso_datetime(datetime(2026, 7, 20, 9, 18)),
            '2026-07-20T09:18:00+00:00',
        )

    def test_aware_datetime_keeps_its_offset(self):
        shanghai = timezone(timedelta(hours=8))
        value = datetime(2026, 7, 20, 17, 18, tzinfo=shanghai)

        self.assertEqual(iso_datetime(value), '2026-07-20T17:18:00+08:00')
        self.assertEqual(datetime.fromisoformat(iso_datetime(value)).astimezone(UTC).hour, 9)
