import unittest
from decimal import Decimal

class TestSalesEvaluationReport(unittest.TestCase):
    def test_actual_sales_calculation(self):
        # Simulate payments collected vs booked contract amount
        booked_contract_amount = Decimal("150000.00")
        payments_collected = Decimal("50000.00")
        cash_flow_sales = Decimal("5000.00")
        
        actual_sales = payments_collected + cash_flow_sales
        self.assertEqual(actual_sales, Decimal("55000.00"))
        self.assertNotEqual(actual_sales, booked_contract_amount)

if __name__ == "__main__":
    unittest.main()
