import unittest
from datetime import date

class TestRepositorySalesEdgeCases(unittest.TestCase):
    def test_leap_year_handling(self):
        leap_date = date(2028, 2, 29)
        self.assertEqual(leap_date.strftime("%Y-%m-%d"), "2028-02-29")

    def test_month_boundary_comparison(self):
        start = date(2026, 11, 1)
        end = date(2026, 11, 30)
        self.assertLess(start, end)
        self.assertEqual((end - start).days, 29)

if __name__ == "__main__":
    unittest.main()
