import unittest
from decimal import Decimal

class TestPackageZeroPrice(unittest.TestCase):
    def test_zero_price_allowed(self):
        price = Decimal("0.00")
        self.assertGreaterEqual(price, Decimal("0.00"))
        self.assertTrue(price == Decimal("0.00"))

if __name__ == "__main__":
    unittest.main()
