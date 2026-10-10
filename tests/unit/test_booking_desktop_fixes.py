import unittest
import sys
import os

# Add Catering_Present/jayraldines_catering to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Catering_Present", "jayraldines_catering")))

class TestBookingDesktopFixes(unittest.TestCase):
    def test_clean_motif_name_import_in_booking_modal(self):
        """Verify clean_motif_name is accessible in booking_modal."""
        from components.booking_modal import clean_motif_name
        self.assertEqual(clean_motif_name("Emerald Green"), "Emerald Green")
        self.assertEqual(clean_motif_name("#2563EB"), "Royal Blue")
        self.assertEqual(clean_motif_name(""), "Standard")

    def test_dish_deduplication_logic(self):
        """Verify duplicated dishes (e.g. raw and set-flattened) are deduplicated correctly."""
        raw_dishes = [
            {"name": "Beef Caldereta", "category": ""},
            {"name": "Buttered Chicken", "category": "Chicken Courses"},
            {"name": "Fish Fillet w/ Tartar Sauce", "category": ""},
            {"name": "Pancit Guisado", "category": ""},
            {"name": "Beef Caldereta", "category": "Set C"},
            {"name": "Buttered Chicken", "category": "Set C"},
            {"name": "Fish Fillet w/ Tartar Sauce", "category": "Set C"},
            {"name": "Pancit Guisado", "category": "Set C"},
        ]
        deduped = []
        seen = {}
        for r in raw_dishes:
            nm = (r.get("name") or "").strip()
            if not nm:
                continue
            key = nm.lower()
            cat = (r.get("category") or "").strip()
            if key not in seen:
                seen[key] = len(deduped)
                deduped.append({"name": nm, "category": cat})
            else:
                idx = seen[key]
                if not deduped[idx]["category"] and cat:
                    deduped[idx]["category"] = cat

        self.assertEqual(len(deduped), 4)
        names = [d["name"] for d in deduped]
        self.assertEqual(names, ["Beef Caldereta", "Buttered Chicken", "Fish Fillet w/ Tartar Sauce", "Pancit Guisado"])
        # Buttered Chicken keeps Chicken Courses, Beef Caldereta gets Set C
        self.assertEqual(deduped[0]["category"], "Set C")
        self.assertEqual(deduped[1]["category"], "Chicken Courses")

    def test_order_print_dialog_html_layout(self):
        """Verify order print dialog uses table-layout:fixed and white-space:nowrap on Downpayment."""
        with open(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Catering_Present", "jayraldines_catering", "components", "order_print_dialog.py")), "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('style="width:100%; table-layout:fixed; border-collapse:collapse;"', content)
        self.assertIn('Downpayment:</td>', content)
        self.assertIn('white-space:nowrap;', content)

    def test_pdf_export_footer(self):
        """Verify export_receipt_pdf renders cleanly to a temp file."""
        import tempfile
        from utils.exporter import export_receipt_pdf
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            sample_booking = {
                "id": "BK-2026-TEST",
                "name": "Test Client",
                "address": "123 Test St",
                "contact": "09123456789",
                "event_date": "2026-10-25",
                "event_time": "12:00 PM",
                "venue": "Test Venue",
                "occasion": "Birthday",
                "motif": "Royal Blue",
                "pax": 50,
                "total": 25000,
                "amount_paid": 10000,
                "package_name": "Standard Package",
                "dishes": [{"name": "Pork Adobo"}, {"name": "Chicken Curry"}],
            }
            res = export_receipt_pdf(tmp_path, {"invoice": "INV-TEST"}, sample_booking)
            self.assertTrue(res)
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 1000)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def test_food_set_selection_and_target_limit(self):
        """Test food set card clicking, stepper, unselecting, and target limit capping."""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])

        from components.booking_modal import BookingModal
        modal = BookingModal()
        modal._order_type = "food_set"
        modal.f_num_sets.setValue(2)  # target: 2 sets

        # Mock packages
        modal._fs_set_packages = [
            {"id": 101, "name": "Food Set A", "price_per_pax": 3500.0, "min_pax": 1, "description": ""},
            {"id": 102, "name": "Food Set B", "price_per_pax": 4000.0, "min_pax": 1, "description": ""},
            {"id": 103, "name": "Food Set C", "price_per_pax": 4500.0, "min_pax": 1, "description": ""},
        ]
        from PySide6.QtWidgets import QSpinBox, QLabel, QPushButton, QFrame
        modal._fs_qty_spins = {101: QSpinBox(), 102: QSpinBox(), 103: QSpinBox()}
        modal._fs_cards = {101: QFrame(), 102: QFrame(), 103: QFrame()}
        modal._fs_badges = {101: QLabel(), 102: QLabel(), 103: QLabel()}
        modal._fs_unselect_btns = {101: QPushButton(), 102: QPushButton(), 103: QPushButton()}
        modal._fs_summary_lbl = QLabel()

        for sp in modal._fs_qty_spins.values():
            sp.setRange(0, 200)
            sp.setValue(0)

        # 1. Click Set A -> selects with qty 1
        modal._on_fs_card_clicked(None, 101)
        self.assertEqual(modal._fs_qty_spins[101].value(), 1)
        self.assertIn("1 / 2 sets", modal._fs_summary_lbl.text())

        # 2. Click Set B -> selects with qty 1 (now 2 / 2 sets)
        modal._on_fs_card_clicked(None, 102)
        self.assertEqual(modal._fs_qty_spins[102].value(), 1)
        self.assertIn("Target met: 2 / 2 sets", modal._fs_summary_lbl.text())

        # 3. Try to click Set C -> blocked because target of 2 is already reached!
        modal._on_fs_card_clicked(None, 103)
        self.assertEqual(modal._fs_qty_spins[103].value(), 0)
        self.assertIn("Target limit of 2 set(s) reached", modal._fs_summary_lbl.text())

        # 4. Unselect Set A -> qty becomes 0 (total now 1 / 2)
        modal._on_fs_unselect(101)
        self.assertEqual(modal._fs_qty_spins[101].value(), 0)
        self.assertIn("1 / 2 sets", modal._fs_summary_lbl.text())

        # 5. Now click Set C -> allowed! (total now 2 / 2)
        modal._on_fs_card_clicked(None, 103)
        self.assertEqual(modal._fs_qty_spins[103].value(), 1)
        self.assertIn("Target met: 2 / 2 sets", modal._fs_summary_lbl.text())

        # 6. Unselect Set B, and use stepper [+] on Set C to get 2 sets of Set C!
        modal._on_fs_unselect(102)
        self.assertEqual(modal._fs_qty_spins[102].value(), 0)
        modal._on_fs_stepper(103, 1)
        self.assertEqual(modal._fs_qty_spins[103].value(), 2)
        self.assertIn("Target met: 2 / 2 sets", modal._fs_summary_lbl.text())

        # 7. Step 2 validation passes when total matches target
        modal._step = 2
        self.assertTrue(modal._validate_current())

        # 8. If under target (e.g. 1 / 2), step 2 validation blocks
        modal._fs_qty_spins[103].setValue(1)
        self.assertFalse(modal._validate_current())
        self.assertIn("Target requirement: 2 sets required", modal._fs_summary_lbl.text())


if __name__ == "__main__":
    unittest.main()
