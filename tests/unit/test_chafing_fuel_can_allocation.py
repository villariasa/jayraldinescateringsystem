import unittest

class TestChafingFuelCanAllocation(unittest.TestCase):
    def test_standard_three_hour_event(self):
        duration_hours = 3
        dish_count = 6
        burn_hours_per_can = 2
        cans_per_dish = (duration_hours + burn_hours_per_can - 1) // burn_hours_per_can
        total_cans = cans_per_dish * dish_count
        self.assertEqual(total_cans, 12)

    def test_five_hour_extended_banquet(self):
        duration_hours = 5
        dish_count = 8
        burn_hours_per_can = 2
        cans_per_dish = (duration_hours + burn_hours_per_can - 1) // burn_hours_per_can
        total_cans = cans_per_dish * dish_count
        self.assertEqual(total_cans, 24)

if __name__ == '__main__':
    unittest.main()
