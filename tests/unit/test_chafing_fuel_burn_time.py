import unittest

class TestChafingFuelBurnTime(unittest.TestCase):
    def test_standard_gel_can_burn_duration(self):
        canister_capacity_grams = 200
        burn_rate_grams_per_hour = 80
        estimated_burn_hours = canister_capacity_grams / burn_rate_grams_per_hour
        self.assertAlmostEqual(estimated_burn_hours, 2.5, places=2)

    def test_outdoor_wind_guard_burn_extension(self):
        baseline_hours = 2.0
        wind_guard_factor = 1.15
        protected_hours = baseline_hours * wind_guard_factor
        self.assertGreater(protected_hours, 2.2)

if __name__ == '__main__':
    unittest.main()
