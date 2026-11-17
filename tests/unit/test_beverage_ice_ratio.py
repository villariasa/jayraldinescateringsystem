import unittest

class TestBeverageIceRatio(unittest.TestCase):
    def test_dispenser_liquid_capacity_with_ice(self):
        dispenser_volume_liters = 20.0
        ice_volume_fraction = 0.30
        liquid_capacity = dispenser_volume_liters * (1.0 - ice_volume_fraction)
        self.assertAlmostEqual(liquid_capacity, 14.0)

    def test_servings_count_at_250ml(self):
        liquid_liters = 14.0
        serving_size_liters = 0.25
        servings = int(liquid_liters / serving_size_liters)
        self.assertEqual(servings, 56)

if __name__ == '__main__':
    unittest.main()
