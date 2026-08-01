from datetime import UTC, datetime, timedelta, timezone
from unittest import TestCase

from app.api.v1.mobile_serializers import iso_datetime
from app.utils.helpers import business_now, now, unix_timestamp, utc_naive


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

    def test_shanghai_datetime_is_converted_to_naive_utc_for_database(self):
        shanghai = timezone(timedelta(hours=8))

        self.assertEqual(
            utc_naive(datetime(2026, 8, 1, 15, 53, tzinfo=shanghai)),
            datetime(2026, 8, 1, 7, 53),
        )

    def test_now_is_naive_utc(self):
        before = datetime.now(UTC).replace(tzinfo=None)
        value = now()
        after = datetime.now(UTC).replace(tzinfo=None)

        self.assertIsNone(value.tzinfo)
        self.assertLessEqual(before, value)
        self.assertLessEqual(value, after)

    def test_business_now_has_shanghai_offset(self):
        self.assertEqual(business_now().utcoffset(), timedelta(hours=8))

    def test_unix_timestamp_does_not_depend_on_naive_datetime(self):
        before = int(datetime.now(UTC).timestamp())
        value = unix_timestamp()
        after = int(datetime.now(UTC).timestamp())

        self.assertLessEqual(before, value)
        self.assertLessEqual(value, after)
