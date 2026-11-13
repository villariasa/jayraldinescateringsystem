import unittest

class TestDeliveryRadiusSurcharge(unittest.TestCase):
    def test_within_free_base_zone(self):
        distance_km = 12
        base_zone_limit_km = 15
        surcharge = 0 if distance_km <= base_zone_limit_km else (distance_km - base_zone_limit_km) * 50
        self.assertEqual(surcharge, 0)

    def test_out_of_town_excess_kilometer_fee(self):
        distance_km = 35
        base_zone_limit_km = 15
        per_km_rate = 60
        surcharge = (distance_km - base_zone_limit_km) * per_km_rate
        self.assertEqual(surcharge, 1200)

if __name__ == '__main__':
    unittest.main()
