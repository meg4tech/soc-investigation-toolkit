import unittest
from datetime import datetime, timedelta, timezone

from soc_toolkit.impossible_travel import (
    InvalidTravelPairError,
    assess_pair,
    calculate_speed_kmh,
    detect_impossible_travel,
    pair_consecutive_logins,
)
from soc_toolkit.models import LoginEvent

LONDON = (51.5074, -0.1278, "London, GB")
PARIS = (48.8566, 2.3522, "Paris, FR")
SYDNEY = (-33.8688, 151.2093, "Sydney, AU")
BASE_TIME = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)


def make_event(user, hours_after_base, place, row, ip="192.0.2.1"):
    lat, lon, location = place
    return LoginEvent(
        user=user,
        timestamp=BASE_TIME + timedelta(hours=hours_after_base),
        ip_address=ip,
        latitude=lat,
        longitude=lon,
        location=location,
        source_row=row,
    )


class TestCalculateSpeed(unittest.TestCase):
    def test_speed_in_kmh(self):
        self.assertEqual(calculate_speed_kmh(900, 3600), 900.0)
        self.assertEqual(calculate_speed_kmh(450, 1800), 900.0)

    def test_duplicate_event_has_zero_speed(self):
        self.assertEqual(calculate_speed_kmh(0, 0), 0.0)

    def test_same_time_different_place_is_invalid(self):
        with self.assertRaises(InvalidTravelPairError):
            calculate_speed_kmh(343.5, 0)

    def test_negative_elapsed_time_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_speed_kmh(100, -1)


class TestPairing(unittest.TestCase):
    def test_pairs_are_per_user_and_time_ordered(self):
        # Interleaved users, and deliberately not in time order.
        a2 = make_event("alice", 5, PARIS, row=2)
        b1 = make_event("bob", 0, LONDON, row=3)
        a1 = make_event("alice", 0, LONDON, row=4)
        a3 = make_event("alice", 24, PARIS, row=5)
        b2 = make_event("bob", 2, SYDNEY, row=6)

        pairs = pair_consecutive_logins([a2, b1, a1, a3, b2])

        self.assertEqual(pairs, [(a1, a2), (a2, a3), (b1, b2)])

    def test_single_login_produces_no_pairs(self):
        self.assertEqual(pair_consecutive_logins([make_event("carol", 0, LONDON, row=2)]), [])

    def test_ordering_uses_utc_not_wall_clock(self):
        # 10:00 at +01:00 is 09:00 UTC, so it is *earlier* than 09:30 UTC.
        paris_local = LoginEvent("alice", datetime(2026, 3, 2, 10, 0, tzinfo=timezone(timedelta(hours=1))),
                                 "192.0.2.1", *PARIS[:2], PARIS[2], source_row=2)
        london_utc = LoginEvent("alice", datetime(2026, 3, 2, 9, 30, tzinfo=timezone.utc),
                                "192.0.2.2", *LONDON[:2], LONDON[2], source_row=3)
        ((first, second),) = pair_consecutive_logins([london_utc, paris_local])
        self.assertIs(first, paris_local)
        self.assertIs(second, london_utc)


class TestDetection(unittest.TestCase):
    def test_impossible_travel_is_flagged(self):
        events = [make_event("bob", 0, LONDON, row=2), make_event("bob", 2, SYDNEY, row=3)]
        (result,) = detect_impossible_travel(events, max_speed_kmh=900)
        self.assertTrue(result.flagged)
        self.assertGreater(result.speed_kmh, 8000)
        self.assertEqual(result.elapsed_seconds, 7200)

    def test_plausible_travel_is_not_flagged(self):
        events = [make_event("alice", 0, LONDON, row=2), make_event("alice", 5, PARIS, row=3)]
        (result,) = detect_impossible_travel(events, max_speed_kmh=900)
        self.assertFalse(result.flagged)

    def test_threshold_boundary(self):
        previous = make_event("alice", 0, LONDON, row=2)
        current = make_event("alice", 1, PARIS, row=3)
        speed = assess_pair(previous, current, 900).speed_kmh

        self.assertTrue(assess_pair(previous, current, speed - 0.001).flagged)
        self.assertFalse(assess_pair(previous, current, speed).flagged)
        self.assertFalse(assess_pair(previous, current, speed + 0.001).flagged)

    def test_threshold_is_recorded_on_the_result(self):
        events = [make_event("alice", 0, LONDON, row=2), make_event("alice", 5, PARIS, row=3)]
        (result,) = detect_impossible_travel(events, max_speed_kmh=123.0)
        self.assertEqual(result.threshold_kmh, 123.0)

    def test_same_timestamp_different_location_is_rejected(self):
        events = [make_event("bob", 0, LONDON, row=2), make_event("bob", 0, SYDNEY, row=3)]
        with self.assertRaises(InvalidTravelPairError) as ctx:
            detect_impossible_travel(events, max_speed_kmh=900)
        self.assertIn("rows 2 and 3", str(ctx.exception))

    def test_duplicate_event_is_not_flagged(self):
        events = [make_event("erin", 0, LONDON, row=2), make_event("erin", 0, LONDON, row=3)]
        (result,) = detect_impossible_travel(events, max_speed_kmh=900)
        self.assertEqual(result.speed_kmh, 0.0)
        self.assertFalse(result.flagged)


if __name__ == "__main__":
    unittest.main()
