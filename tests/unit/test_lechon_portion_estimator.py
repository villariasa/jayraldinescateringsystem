import unittest

class TestLechonPortionEstimator(unittest.TestCase):
    def test_raw_to_cooked_yield(self):
        raw_belly_kg = 5.0
        yield_rate = 0.65
        cooked_kg = raw_belly_kg * yield_rate
        self.assertAlmostEqual(cooked_kg, 3.25)

    def test_buffet_portions_at_150g(self):
        cooked_kg = 3.25
        portion_kg = 0.15
        portions = int(cooked_kg / portion_kg)
        self.assertEqual(portions, 21)

if __name__ == '__main__':
    unittest.main()
