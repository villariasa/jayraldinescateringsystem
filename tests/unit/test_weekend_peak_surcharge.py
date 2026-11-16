import unittest

class TestWeekendPeakSurcharge(unittest.TestCase):
    def test_regular_weekday_no_surcharge(self):
        bill = 50000.00
        is_december_peak = False
        surcharge = bill * 0.10 if is_december_peak else 0.0
        self.assertEqual(surcharge, 0.0)

    def test_december_weekend_peak_surcharge(self):
        bill = 50000.00
        is_december_peak = True
        surcharge = bill * 0.10 if is_december_peak else 0.0
        self.assertEqual(surcharge, 5000.00)

if __name__ == '__main__':
    unittest.main()
