"""Data records passed between the loader, detection and report stages.

Both records are frozen (read-only) so that evidence cannot be modified
accidentally after it has been loaded and validated.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LoginEvent:
    """A single validated authentication event."""

    user: str
    timestamp: datetime  # Always timezone-aware and normalised to UTC by the loader.
    ip_address: str
    latitude: float
    longitude: float
    location: str
    # Line number in the input file, so every finding can be traced back to
    # the exact evidence it was derived from.
    source_row: int


@dataclass(frozen=True)
class TravelAssessment:
    """The result of comparing two consecutive logins for the same user."""

    user: str
    previous: LoginEvent
    current: LoginEvent
    distance_km: float
    elapsed_seconds: float
    speed_kmh: float
    threshold_kmh: float
    flagged: bool
