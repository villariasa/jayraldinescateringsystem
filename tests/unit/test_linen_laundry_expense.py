import unittest

def calculate_laundry_cost(tablecloths, chair_covers, napkins, rates=None):
    if rates is None:
        rates = {"tablecloth": 25.0, "chair_cover": 8.0, "napkin": 3.0}
    total = (tablecloths * rates["tablecloth"] +
             chair_covers * rates["chair_cover"] +
             napkins * rates["napkin"])
    return round(total, 2)

class TestLinenLaundryExpense(unittest.TestCase):
    def test_standard_banquet_linen_cost(self):
        # 10 tablecloths (250) + 100 chair covers (800) + 100 napkins (300) = 1350.0
        self.assertEqual(calculate_laundry_cost(10, 100, 100), 1350.0)

    def test_zero_linens(self):
        self.assertEqual(calculate_laundry_cost(0, 0, 0), 0.0)

if __name__ == "__main__":
    unittest.main()
