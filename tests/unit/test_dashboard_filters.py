import unittest
import datetime

class TestDashboardDateFilters(unittest.TestCase):
    def test_today_range(self):
        today = datetime.date.today()
        start = today.strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        self.assertEqual(start, end)

    def test_week_range(self):
        today = datetime.date.today()
        mon = today - datetime.timedelta(days=today.weekday())
        sun = mon + datetime.timedelta(days=6)
        self.assertLessEqual(mon, sun)
        self.assertEqual((sun - mon).days, 6)

if __name__ == "__main__":
    unittest.main()
