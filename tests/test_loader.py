import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from soc_toolkit.loader import InputValidationError, load_login_events

HEADER = "user,timestamp,ip_address,latitude,longitude,location\n"
VALID_ROW = 'alice@example.com,2026-03-02T09:00:00+00:00,192.0.2.10,51.5074,-0.1278,"London, GB"\n'
SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample" / "synthetic_logins.csv"


class LoaderTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def write_csv(self, text: str) -> Path:
        path = Path(self._tmp.name) / "input.csv"
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def assert_rejected(self, text: str, message_fragment: str):
        with self.assertRaises(InputValidationError) as ctx:
            load_login_events(self.write_csv(text))
        self.assertIn(message_fragment, str(ctx.exception))


class TestValidInput(LoaderTestCase):
    def test_loads_sample_data(self):
        events = load_login_events(SAMPLE)
        self.assertEqual(len(events), 12)

    def test_timestamps_are_normalised_to_utc(self):
        events = load_login_events(SAMPLE)
        dave_new_york = next(e for e in events if e.location == "New York, US")
        # 22:00 at -05:00 is 03:00 UTC the next day.
        self.assertEqual(dave_new_york.timestamp, datetime(2026, 3, 2, 3, 0, tzinfo=timezone.utc))

    def test_z_suffix_is_accepted_as_utc(self):
        row = VALID_ROW.replace("+00:00", "Z")
        (event,) = load_login_events(self.write_csv(HEADER + row))
        self.assertEqual(event.timestamp.utcoffset().total_seconds(), 0)

    def test_parses_fields_and_records_source_row(self):
        (event,) = load_login_events(self.write_csv(HEADER + VALID_ROW))
        self.assertEqual(event.user, "alice@example.com")
        self.assertEqual(event.ip_address, "192.0.2.10")
        self.assertEqual(event.latitude, 51.5074)
        self.assertEqual(event.longitude, -0.1278)
        self.assertEqual(event.location, "London, GB")
        self.assertEqual(event.source_row, 2)

    def test_user_is_normalised_to_lower_case(self):
        row = VALID_ROW.replace("alice@example.com", "Alice@Example.com")
        (event,) = load_login_events(self.write_csv(HEADER + row))
        self.assertEqual(event.user, "alice@example.com")

    def test_ipv6_is_canonicalised(self):
        row = VALID_ROW.replace("192.0.2.10", "2001:DB8:0:0:0:0:0:1")
        (event,) = load_login_events(self.write_csv(HEADER + row))
        self.assertEqual(event.ip_address, "2001:db8::1")


class TestInvalidInput(LoaderTestCase):
    def test_missing_file(self):
        with self.assertRaises(InputValidationError):
            load_login_events(Path(self._tmp.name) / "does_not_exist.csv")

    def test_empty_file(self):
        self.assert_rejected("", "no header row")

    def test_header_only(self):
        self.assert_rejected(HEADER, "no login events")

    def test_missing_column(self):
        self.assert_rejected("user,timestamp,ip_address,latitude,longitude\n", "location")

    def test_duplicate_column(self):
        text = HEADER.rstrip("\n") + ",latitude\n" + VALID_ROW.rstrip("\n") + ",-33.8688\n"
        self.assert_rejected(text, "duplicate columns")

    def test_duplicate_column_differing_in_case_and_spaces(self):
        text = HEADER.rstrip("\n") + ", Latitude\n" + VALID_ROW.rstrip("\n") + ",-33.8688\n"
        self.assert_rejected(text, "duplicate columns")

    def test_missing_value(self):
        self.assert_rejected(HEADER + VALID_ROW.replace("192.0.2.10", ""), "ip_address")

    def test_extra_values(self):
        self.assert_rejected(HEADER + VALID_ROW.rstrip("\n") + ",unexpected\n", "more values")

    def test_timestamp_without_timezone(self):
        self.assert_rejected(HEADER + VALID_ROW.replace("+00:00", ""), "no timezone offset")

    def test_malformed_timestamp(self):
        self.assert_rejected(
            HEADER + VALID_ROW.replace("2026-03-02T09:00:00+00:00", "02/03/2026 09:00"),
            "not ISO 8601",
        )

    def test_invalid_ip_address(self):
        self.assert_rejected(HEADER + VALID_ROW.replace("192.0.2.10", "192.0.2.300"), "invalid IP")

    def test_latitude_out_of_range(self):
        self.assert_rejected(HEADER + VALID_ROW.replace("51.5074", "91"), "latitude")

    def test_longitude_out_of_range(self):
        self.assert_rejected(HEADER + VALID_ROW.replace("-0.1278", "-180.5"), "longitude")

    def test_non_numeric_coordinate(self):
        self.assert_rejected(HEADER + VALID_ROW.replace("51.5074", "north"), "not a number")

    def test_nan_coordinate(self):
        self.assert_rejected(HEADER + VALID_ROW.replace("51.5074", "nan"), "latitude")

    def test_control_characters_are_rejected(self):
        # An ANSI escape sequence that would recolour the analyst's terminal.
        row = VALID_ROW.replace("London, GB", "\x1b[31mLondon, GB")
        self.assert_rejected(HEADER + row, "control")

    def test_error_names_the_row(self):
        text = HEADER + VALID_ROW + VALID_ROW.replace("192.0.2.10", "bad-ip")
        self.assert_rejected(text, "Row 3")


if __name__ == "__main__":
    unittest.main()
