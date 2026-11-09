import unittest

def calculate_invoice_totals(subtotal, is_tax_exempt=False, vat_rate=0.12):
    if is_tax_exempt:
        return {"subtotal": subtotal, "vat": 0.0, "total": subtotal}
    vat = round(subtotal * vat_rate, 2)
    return {"subtotal": subtotal, "vat": vat, "total": round(subtotal + vat, 2)}

class TestInvoiceTaxExemption(unittest.TestCase):
    def test_standard_taxable_invoice(self):
        res = calculate_invoice_totals(10000.0, is_tax_exempt=False)
        self.assertEqual(res["vat"], 1200.0)
        self.assertEqual(res["total"], 11200.0)

    def test_senior_or_pwd_exempt_invoice(self):
        res = calculate_invoice_totals(10000.0, is_tax_exempt=True)
        self.assertEqual(res["vat"], 0.0)
        self.assertEqual(res["total"], 10000.0)

if __name__ == "__main__":
    unittest.main()
