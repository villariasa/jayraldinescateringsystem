import unittest

def validate_headcount(count, min_count=30, max_count=1000):
    return isinstance(count, int) and min_count <= count <= max_count

class TestBanquetHeadcountValidation(unittest.TestCase):
    def test_valid_headcount(self):
        self.assertTrue(validate_headcount(100))
        self.assertTrue(validate_headcount(30))
        self.assertTrue(validate_headcount(1000))

    def test_invalid_low_headcount(self):
        self.assertFalse(validate_headcount(25))

    def test_invalid_excessive_headcount(self):
        self.assertFalse(validate_headcount(1500))

if __name__ == "__main__":
    unittest.main()
