import unittest

class TestEarlyBirdDiscountRules(unittest.TestCase):
    def test_sixty_days_advance_discount(self):
        total_bill = 60000.00
        discount_rate = 0.05
        max_discount_cap = 2500.00
        discount = min(total_bill * discount_rate, max_discount_cap)
        self.assertEqual(discount, 2500.00)

    def test_small_package_within_cap(self):
        total_bill = 30000.00
        discount_rate = 0.05
        max_discount_cap = 2500.00
        discount = min(total_bill * discount_rate, max_discount_cap)
        self.assertEqual(discount, 1500.00)

if __name__ == '__main__':
    unittest.main()
