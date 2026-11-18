import unittest

class TestWaiterShiftOvertimePay(unittest.TestCase):
    def test_standard_eight_hour_shift(self):
        hours_worked = 8.0
        base_hourly_rate = 75.00
        overtime_hours = max(0.0, hours_worked - 8.0)
        total_pay = (min(hours_worked, 8.0) * base_hourly_rate) + (overtime_hours * base_hourly_rate * 1.25)
        self.assertEqual(total_pay, 600.00)

    def test_extended_ten_hour_shift(self):
        hours_worked = 10.0
        base_hourly_rate = 75.00
        overtime_hours = max(0.0, hours_worked - 8.0)
        total_pay = (min(hours_worked, 8.0) * base_hourly_rate) + (overtime_hours * base_hourly_rate * 1.25)
        self.assertEqual(total_pay, 787.50)

if __name__ == '__main__':
    unittest.main()
