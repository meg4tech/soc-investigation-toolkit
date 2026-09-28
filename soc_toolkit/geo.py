"""Geographic distance calculation."""

import math

# Mean Earth radius (IUGG). The Earth is not a perfect sphere, so haversine
# distances can differ from true geodesic distances by up to ~0.5%. That is
# far smaller than typical IP geolocation error, so it is acceptable here.
EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres between two points.

    The great-circle distance is the shortest path over the Earth's surface,
    so it is the most generous (lowest) distance a traveller could cover.
    Using it means the required speed we calculate is a lower bound, which
    avoids overstating how suspicious a pair of logins is.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    # Floating-point rounding can push `a` fractionally above 1 for
    # near-antipodal points, which would make sqrt/asin fail.
    a = min(1.0, a)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
