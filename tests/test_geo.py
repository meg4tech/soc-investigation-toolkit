import math
import unittest

from soc_toolkit.geo import EARTH_RADIUS_KM, haversine_km

LONDON = (51.5074, -0.1278)
PARIS = (48.8566, 2.3522)
SYDNEY = (-33.8688, 151.2093)


class TestHaversine(unittest.TestCase):
    def test_same_point_is_zero(self):
        self.assertEqual(haversine_km(*LONDON, *LONDON), 0.0)

    def test_known_distance(self):
        # Published great-circle distance London-Paris is ~343.5 km.
        self.assertAlmostEqual(haversine_km(*LONDON, *PARIS), 343.5, delta=1.0)

    def test_long_distance(self):
        # Published great-circle distance London-Sydney is ~16,990 km.
        self.assertAlmostEqual(haversine_km(*LONDON, *SYDNEY), 16990, delta=20)

    def test_is_symmetric(self):
        self.assertAlmostEqual(
            haversine_km(*LONDON, *SYDNEY), haversine_km(*SYDNEY, *LONDON)
        )

    def test_antipodal_points_are_half_circumference(self):
        self.assertAlmostEqual(haversine_km(0, 0, 0, 180), math.pi * EARTH_RADIUS_KM)

    def test_crossing_the_antimeridian_takes_the_short_way(self):
        # 179E to 179W is 2 degrees apart, not 358.
        expected = 2 * math.pi * EARTH_RADIUS_KM * 2 / 360
        self.assertAlmostEqual(haversine_km(0, 179, 0, -179), expected)


if __name__ == "__main__":
    unittest.main()
