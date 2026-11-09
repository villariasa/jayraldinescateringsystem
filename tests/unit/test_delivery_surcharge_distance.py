import unittest

def calculate_delivery_fee(distance_km, free_radius_km=20, rate_per_km=50.0):
    if distance_km <= free_radius_km:
        return 0.0
    extra_km = distance_km - free_radius_km
    return round(extra_km * rate_per_km, 2)

class TestDeliverySurchargeDistance(unittest.TestCase):
    def test_within_free_radius(self):
        self.assertEqual(calculate_delivery_fee(15.0), 0.0)
        self.assertEqual(calculate_delivery_fee(20.0), 0.0)

    def test_out_of_town_surcharge(self):
        # 35 km -> 15 extra km * 50 = 750.0
        self.assertEqual(calculate_delivery_fee(35.0), 750.0)

if __name__ == "__main__":
    unittest.main()
