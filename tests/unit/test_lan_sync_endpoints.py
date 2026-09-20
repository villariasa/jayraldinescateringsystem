import unittest

class TestLANSyncEndpoints(unittest.TestCase):
    def test_heartbeat_payload_structure(self):
        payload = {
            "device_id": "tablet-kiosk-01",
            "device_name": "Front Desk Kiosk",
            "status": "online"
        }
        self.assertIn("device_id", payload)
        self.assertEqual(payload["status"], "online")

if __name__ == "__main__":
    unittest.main()
