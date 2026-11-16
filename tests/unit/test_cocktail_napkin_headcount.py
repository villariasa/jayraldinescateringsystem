import unittest

class TestCocktailNapkinHeadcount(unittest.TestCase):
    def test_standard_napkin_estimate(self):
        guests = 150
        napkins_per_guest = 3
        total_napkins = guests * napkins_per_guest
        self.assertEqual(total_napkins, 450)

    def test_with_cocktail_buffer(self):
        guests = 200
        napkins_per_guest = 4
        buffer_percent = 0.15
        base = guests * napkins_per_guest
        total = int(round(base * (1 + buffer_percent)))
        self.assertEqual(total, 920)

if __name__ == '__main__':
    unittest.main()
