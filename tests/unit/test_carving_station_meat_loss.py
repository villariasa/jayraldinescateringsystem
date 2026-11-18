import unittest

class TestCarvingStationMeatLoss(unittest.TestCase):
    def test_roast_beef_trim_loss(self):
        gross_roast_kg = 10.0
        trim_loss_percent = 0.12
        net_carved_kg = gross_roast_kg * (1.0 - trim_loss_percent)
        self.assertAlmostEqual(net_carved_kg, 8.8)

    def test_portion_count_at_120g(self):
        net_carved_kg = 8.8
        portion_kg = 0.12
        portions = int(net_carved_kg / portion_kg)
        self.assertEqual(portions, 73)

if __name__ == '__main__':
    unittest.main()
