import unittest

class TestDeviceHeartbeatTelemetry(unittest.TestCase):
    def test_heartbeat_packet_validation(self):
        packet = {
            "device_uuid": "POS-TAB-101",
            "battery_pct": 94,
            "ip_address": "192.168.1.101",
            "rssi_dbm": -58
        }
        self.assertGreaterEqual(packet["battery_pct"], 0)
        self.assertLessEqual(packet["battery_pct"], 100)
        self.assertTrue(packet["ip_address"].startswith("192.168."))

if __name__ == "__main__":
    unittest.main()
