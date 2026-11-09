import unittest

def is_downpayment_sufficient(downpayment, contract_total, required_pct=0.50):
    min_required = round(contract_total * required_pct, 2)
    return downpayment >= min_required

class TestDownpaymentThreshold(unittest.TestCase):
    def test_exact_fifty_percent(self):
        self.assertTrue(is_downpayment_sufficient(25000, 50000))

    def test_insufficient_deposit(self):
        self.assertFalse(is_downpayment_sufficient(20000, 50000))

    def test_full_payment(self):
        self.assertTrue(is_downpayment_sufficient(50000, 50000))

if __name__ == "__main__":
    unittest.main()
