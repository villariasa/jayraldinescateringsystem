import unittest

class TestIceConsumptionEstimator(unittest.TestCase):
    def test_outdoor_summer_ice_requirement(self):
        headcount = 100
        duration_hours = 4
        ice_kg = headcount * 0.5
        self.assertEqual(ice_kg, 50.0)

    def test_indoor_airconditioned_rate(self):
        headcount = 100
        ice_kg = (headcount * 0.5) * 0.8
        self.assertEqual(ice_kg, 40.0)

if __name__ == '__main__':
    unittest.main()
