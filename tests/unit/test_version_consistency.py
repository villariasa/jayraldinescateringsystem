import unittest
import re

class TestVersionConsistency(unittest.TestCase):
    def test_version_format(self):
        v = "4.7.6"
        match = re.match(r"^\d+\.\d+\.\d+$", v)
        self.assertIsNotNone(match)

if __name__ == "__main__":
    unittest.main()
