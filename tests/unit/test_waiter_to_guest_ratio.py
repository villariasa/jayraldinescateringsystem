import unittest

class TestWaiterToGuestRatio(unittest.TestCase):
    def test_plated_service_ratio(self):
        guests = 120
        waiters = (guests + 14) // 15
        self.assertEqual(waiters, 8)

    def test_buffet_service_ratio(self):
        guests = 120
        waiters = (guests + 24) // 25
        self.assertEqual(waiters, 5)

if __name__ == '__main__':
    unittest.main()
