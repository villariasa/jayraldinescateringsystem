import unittest

def calculate_deposit(total_amount, pct=0.50):
    return round(total_amount * pct, 2)

class TestBookingDepositCalculation(unittest.TestCase):
    def test_standard_fifty_pct_deposit(self):
        self.assertEqual(calculate_deposit(50000.0), 25000.0)

    def test_deposit_with_cents(self):
        self.assertEqual(calculate_deposit(75432.50), 37716.25)

if __name__ == "__main__":
    unittest.main()
