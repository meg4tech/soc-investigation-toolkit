"""Impossible Travel detection.

For each user, logins are sorted by time and each login is compared with the
next one. If the speed needed to travel between the two locations in the
time available exceeds the threshold, the pair is flagged for investigation.

This module performs no file I/O and prints nothing, so it can be tested
with in-memory events and reused by future interfaces.
"""

from collections import defaultdict

from .geo import haversine_km
from .models import LoginEvent, TravelAssessment

SECONDS_PER_HOUR = 3600


class InvalidTravelPairError(ValueError):
    """Raised when two logins cannot be assessed because the data is contradictory."""


def calculate_speed_kmh(distance_km: float, elapsed_seconds: float) -> float:
    """Return the speed in km/h needed to cover `distance_km` in `elapsed_seconds`."""
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must not be negative")
    if elapsed_seconds == 0:
        if distance_km == 0:
            # Same place at the same moment: a duplicate event, not travel.
            return 0.0
        # One account in two places at the same instant cannot be expressed
        # as a speed. It points to a data problem (clock skew, merged log
        # sources) that an analyst must resolve before the pair is trusted.
        raise InvalidTravelPairError(
            "logins at the same timestamp from different locations cannot be assessed"
        )
    return distance_km / (elapsed_seconds / SECONDS_PER_HOUR)


def pair_consecutive_logins(events: list[LoginEvent]) -> list[tuple[LoginEvent, LoginEvent]]:
    """Group events by user, sort each user's events by time, and pair neighbours."""
    by_user: dict[str, list[LoginEvent]] = defaultdict(list)
    for event in events:
        by_user[event.user].append(event)

    pairs = []
    for user in sorted(by_user):
        # source_row breaks timestamp ties so results are deterministic.
        ordered = sorted(by_user[user], key=lambda e: (e.timestamp, e.source_row))
        pairs.extend(zip(ordered, ordered[1:]))
    return pairs


def assess_pair(
    previous: LoginEvent, current: LoginEvent, max_speed_kmh: float
) -> TravelAssessment:
    """Calculate distance, elapsed time and required speed for one login pair."""
    distance_km = haversine_km(
        previous.latitude, previous.longitude, current.latitude, current.longitude
    )
    elapsed_seconds = (current.timestamp - previous.timestamp).total_seconds()

    try:
        speed_kmh = calculate_speed_kmh(distance_km, elapsed_seconds)
    except InvalidTravelPairError as exc:
        raise InvalidTravelPairError(
            f"User {current.user}: rows {previous.source_row} and {current.source_row} - {exc}"
        ) from exc

    return TravelAssessment(
        user=current.user,
        previous=previous,
        current=current,
        distance_km=distance_km,
        elapsed_seconds=elapsed_seconds,
        speed_kmh=speed_kmh,
        threshold_kmh=max_speed_kmh,
        # Strictly greater than: a speed exactly at the threshold is still
        # considered achievable.
        flagged=speed_kmh > max_speed_kmh,
    )


def detect_impossible_travel(
    events: list[LoginEvent], max_speed_kmh: float
) -> list[TravelAssessment]:
    """Assess every consecutive login pair. Flagged and unflagged pairs are returned."""
    return [
        assess_pair(previous, current, max_speed_kmh)
        for previous, current in pair_consecutive_logins(events)
    ]
