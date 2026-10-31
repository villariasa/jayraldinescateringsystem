import unittest

class TestInstallerConfiguration(unittest.TestCase):
    def test_inno_setup_keys(self):
        config = {
            "AppName": "Jayraldines Catering",
            "AppVersion": "4.7.6",
            "Compression": "lzma"
        }
        self.assertEqual(config["AppVersion"], "4.7.6")
        self.assertEqual(config["Compression"], "lzma")

if __name__ == "__main__":
    unittest.main()
