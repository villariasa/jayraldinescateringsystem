import unittest

def is_warmer_safe(water_temp_c, min_threshold_c=65.0):
    return water_temp_c >= min_threshold_c

class TestWarmerTempThreshold(unittest.TestCase):
    def test_safe_temperature(self):
        self.assertTrue(is_warmer_safe(72.5))
        self.assertTrue(is_warmer_safe(65.0))

    def test_unsafe_low_temperature(self):
        self.assertFalse(is_warmer_safe(58.0))
        self.assertFalse(is_warmer_safe(64.9))

if __name__ == "__main__":
    unittest.main()
