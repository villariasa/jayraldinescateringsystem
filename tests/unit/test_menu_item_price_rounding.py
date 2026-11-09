import unittest

def round_menu_price(amount):
    return round(amount, 2)

class TestMenuItemPriceRounding(unittest.TestCase):
    def test_price_rounding(self):
        self.assertEqual(round_menu_price(450.555), 450.56)
        self.assertEqual(round_menu_price(120.001), 120.00)

if __name__ == "__main__":
    unittest.main()
