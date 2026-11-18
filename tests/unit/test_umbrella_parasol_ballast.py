import unittest

class TestUmbrellaParasolBallast(unittest.TestCase):
    def test_sheltered_patio_ballast(self):
        canopy_diameter_m = 2.5
        base_kg = canopy_diameter_m * 10
        self.assertEqual(base_kg, 25.0)

    def test_open_lawn_wind_ballast(self):
        canopy_diameter_m = 2.5
        wind_factor = 1.6
        required_kg = (canopy_diameter_m * 10) * wind_factor
        self.assertEqual(required_kg, 40.0)

if __name__ == '__main__':
    unittest.main()
