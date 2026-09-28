import unittest
from datetime import datetime, timedelta, timezone

from soc_toolkit.config import DetectionConfig
from soc_toolkit.impossible_travel import detect_impossible_travel
from soc_toolkit.models import LoginEvent
from soc_toolkit.report import format_report

CONFIG = DetectionConfig(900.0, "built-in default")
BASE_TIME = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)


def make_event(hours_after_base, lat, lon, location, row):
    return LoginEvent(
        user="bob@example.com",
        timestamp=BASE_TIME + timedelta(hours=hours_after_base),
        ip_address=f"192.0.2.{row}",
        latitude=lat,
        longitude=lon,
        location=location,
        source_row=row,
    )


def build_report(events):
    return format_report(events, detect_impossible_travel(events, CONFIG.max_speed_kmh), CONFIG, "input.csv")


class TestReport(unittest.TestCase):
    def setUp(self):
        self.impossible = [
            make_event(0, 51.5074, -0.1278, "London, GB", row=2),
            make_event(2, -33.8688, 151.2093, "Sydney, AU", row=3),
        ]
        self.plausible = [
            make_event(0, 51.5074, -0.1278, "London, GB", row=2),
            make_event(5, 48.8566, 2.3522, "Paris, FR", row=3),
        ]

    def test_finding_contains_evidence_and_investigation_label(self):
        report = build_report(self.impossible)
        self.assertIn("FINDING 1 of 1: Impossible travel - REQUIRES ANALYST INVESTIGATION", report)
        self.assertIn("bob@example.com", report)
        self.assertIn("2026-03-02 09:00:00 UTC | 192.0.2.2 | London, GB", report)
        self.assertIn("[row 3]", report)
        self.assertIn("Elapsed time     : 2h 00m 00s", report)
        self.assertIn("Suggested analyst checks:", report)

    def test_no_findings_message(self):
        report = build_report(self.plausible)
        self.assertIn("No login pairs exceeded the speed threshold.", report)
        self.assertIn("does not rule out account compromise", report)
        self.assertNotIn("FINDING", report)

    def test_every_report_states_it_is_not_a_determination(self):
        for events in (self.impossible, self.plausible):
            report = build_report(events)
            self.assertIn("NOT a determination", report)
            self.assertIn("Known limitations:", report)

    def test_threshold_and_source_are_shown(self):
        report = build_report(self.plausible)
        self.assertIn("Speed threshold  : 900.0 km/h (source: built-in default)", report)


if __name__ == "__main__":
    unittest.main()
