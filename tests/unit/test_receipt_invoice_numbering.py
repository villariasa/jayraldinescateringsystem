import unittest

def format_invoice_number(prefix, sequence_num):
    return f"{prefix}-{sequence_num:06d}"

class TestReceiptInvoiceNumbering(unittest.TestCase):
    def test_invoice_padding(self):
        self.assertEqual(format_invoice_number("INV", 42), "INV-000042")
        self.assertEqual(format_invoice_number("INV", 10050), "INV-010050")

if __name__ == "__main__":
    unittest.main()
