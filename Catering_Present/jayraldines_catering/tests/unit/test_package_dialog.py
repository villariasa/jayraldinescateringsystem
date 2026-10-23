import sys
import unittest
from PySide6.QtWidgets import QApplication

import utils.repository as repo
from ui.menu_page import PackageDialog


class TestPackageDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        if not repo.db.is_available():
            repo.db.connect()

    def test_package_dialog_dimensions_and_screen_containment(self):
        """Verify PackageDialog stays within screen bounds and does not overlap the screen."""
        dlg = PackageDialog()
        screen = self.app.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # Dialog target dimensions should never exceed 90% of screen height
            self.assertLessEqual(dlg.height(), int(avail.height() * 0.90))
            self.assertLessEqual(dlg.width(), avail.width())
            # Minimum size hint must be compact enough for small/scaled displays (< 500px height)
            self.assertLessEqual(dlg.minimumSizeHint().height(), 500)

    def test_package_dialog_layout_and_elements(self):
        """Verify PackageDialog has responsive photo preview and scrollable fields."""
        dlg = PackageDialog()
        self.assertFalse(dlg._edit_mode)
        self.assertEqual(dlg.windowTitle(), "Add Package")

        # Left column elements
        self.assertTrue(hasattr(dlg, "_img_holder"))
        self.assertTrue(hasattr(dlg, "img_preview"))
        self.assertTrue(hasattr(dlg, "_img_chip"))
        self.assertTrue(hasattr(dlg, "_thumb_lbl"))
        self.assertTrue(hasattr(dlg, "remove_img_btn"))

        # Right column fields
        self.assertTrue(hasattr(dlg, "name_field"))
        self.assertTrue(hasattr(dlg, "price_field"))
        self.assertTrue(hasattr(dlg, "min_pax_field"))
        self.assertTrue(hasattr(dlg, "chk_is_set"))
        self.assertTrue(hasattr(dlg, "chk_is_food_service"))
        self.assertTrue(hasattr(dlg, "desc_field"))
        self.assertTrue(hasattr(dlg, "_inclusions_container"))
        self.assertTrue(hasattr(dlg, "_buckets_container"))

    def test_package_dialog_add_and_save(self):
        """Verify adding a new package, toggling options, and collecting results."""
        dlg = PackageDialog()
        dlg.name_field.setText("Fiesta Buffet Special")
        dlg.price_field.setValue(450.0)
        dlg.min_pax_field.setValue(60)
        dlg.chk_is_set.setChecked(True)
        dlg._add_inclusion_row("Unlimited Fresh Buko Juice")

        dlg._save()
        res = dlg.get_result()
        self.assertIsNotNone(res)
        self.assertEqual(res["name"], "Fiesta Buffet Special")
        self.assertEqual(res["price_per_pax"], 450.0)
        self.assertEqual(res["min_pax"], 60)
        self.assertTrue(res["is_set"])
        self.assertFalse(res["is_food_service"])
        self.assertIn("Unlimited Fresh Buko Juice", res["inclusions"])

    def test_package_dialog_edit_mode(self):
        """Verify pre-filling existing package data in edit mode."""
        pkg_data = {
            "id": 101,
            "name": "Corporate Seminar Package",
            "price_per_pax": 600.0,
            "min_pax": 30,
            "description": "Includes morning snacks, lunch buffet, and afternoon snacks.",
        }
        dlg = PackageDialog(pkg_data=pkg_data)
        self.assertTrue(dlg._edit_mode)
        self.assertEqual(dlg.windowTitle(), "Edit Package")
        self.assertEqual(dlg.name_field.text(), "Corporate Seminar Package")
        self.assertEqual(dlg.price_field.value(), 600.0)
        self.assertEqual(dlg.min_pax_field.value(), 30)
        self.assertEqual(dlg.desc_field.toPlainText(), pkg_data["description"])


if __name__ == "__main__":
    unittest.main()
