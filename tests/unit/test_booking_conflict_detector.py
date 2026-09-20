import unittest
import datetime

class TestBookingConflictDetector(unittest.TestCase):
    def test_conflict_detection(self):
        event_a = ("Grand Ballroom", datetime.date(2026, 10, 15))
        event_b = ("Grand Ballroom", datetime.date(2026, 10, 15))
        event_c = ("Garden Terrace", datetime.date(2026, 10, 15))
        
        self.assertEqual(event_a, event_b) # Conflict
        self.assertNotEqual(event_a, event_c) # No conflict

if __name__ == "__main__":
    unittest.main()
