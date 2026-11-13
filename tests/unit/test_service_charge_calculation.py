import unittest

class TestServiceChargeCalculation(unittest.TestCase):
    def test_regular_event_service_charge_ten_percent(self):
        food_total = 85000.00
        service_rate = 0.10
        service_fee = food_total * service_rate
        self.assertAlmostEqual(service_fee, 8500.00)

    def test_special_holiday_service_charge(self):
        food_total = 85000.00
        holiday_rate = 0.15
        service_fee = food_total * holiday_rate
        self.assertAlmostEqual(service_fee, 12750.00)

if __name__ == '__main__':
    unittest.main()
