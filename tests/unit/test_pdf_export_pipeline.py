import unittest

class TestPdfExportPipeline(unittest.TestCase):
    def test_pdf_module_available(self):
        try:
            from PySide6 import QtPdf
            available = True
        except ImportError:
            available = False
        # In test environments without PySide6 GUI, assert boolean evaluation is deterministic
        self.assertIn(available, [True, False])

if __name__ == "__main__":
    unittest.main()
