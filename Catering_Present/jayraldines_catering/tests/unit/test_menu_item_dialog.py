import sys
import unittest
from PySide6.QtWidgets import QApplication

import utils.repository as repo
from ui.menu_page import MenuItemDialog, AddMenuItemDialog


class TestMenuItemDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        if not repo.db.is_available():
            repo.db.connect()

    def test_menu_item_dialog_layout_and_image_position(self):
        """Verify MenuItemDialog has 2-column layout with left image position matching PackageDialog."""
        dlg = MenuItemDialog()
        self.assertFalse(dlg._edit_mode)
        self.assertEqual(dlg.windowTitle(), "Add Menu Item")

        # Verify left column image holder and elements matching PackageDialog
        self.assertTrue(hasattr(dlg, "_img_holder"))
        self.assertTrue(hasattr(dlg, "img_preview"))
        self.assertTrue(hasattr(dlg, "_img_chip"))
        self.assertEqual(dlg._img_chip.text(), "🍽  Dish Photo")
        self.assertTrue(hasattr(dlg, "_thumb_lbl"))
        self.assertTrue(hasattr(dlg, "remove_img_btn"))

        # Verify right column fields
        self.assertTrue(hasattr(dlg, "item_field"))
        self.assertTrue(hasattr(dlg, "desc_field"))
        self.assertTrue(hasattr(dlg, "cat_field"))
        self.assertTrue(hasattr(dlg, "pkg_field"))
        self.assertTrue(hasattr(dlg, "price_field"))
        self.assertTrue(hasattr(dlg, "status_field"))

    def test_menu_item_dialog_edit_mode_and_save(self):
        """Verify pre-filling existing data in edit mode and saving results."""
        item_data = {
            "id": 99,
            "item": "Crispy Pork Belly",
            "description": "Crispy skin roasted pork belly with spiced liver dip",
            "category": "Main Course",
            "package": "Premium",
            "price": 520.0,
            "status": "Available",
            "image": "",
        }
        dlg = MenuItemDialog(item_data=item_data)
        self.assertTrue(dlg._edit_mode)
        self.assertEqual(dlg.windowTitle(), "Edit Menu Item")
        self.assertEqual(dlg.item_field.text(), "Crispy Pork Belly")
        self.assertEqual(dlg.desc_field.toPlainText(), "Crispy skin roasted pork belly with spiced liver dip")
        self.assertEqual(dlg.price_field.value(), 520.0)

        # Trigger save
        dlg._save()
        res = dlg.get_result()
        self.assertIsNotNone(res)
        self.assertEqual(res["item"], "Crispy Pork Belly")
        self.assertEqual(res["description"], "Crispy skin roasted pork belly with spiced liver dip")
        self.assertEqual(res["price"], 520.0)

    def test_add_menu_item_dialog_compatibility(self):
        """Verify AddMenuItemDialog inherits from MenuItemDialog and provides identical interface."""
        dlg = AddMenuItemDialog()
        self.assertIsInstance(dlg, MenuItemDialog)
        self.assertFalse(dlg._edit_mode)
        self.assertEqual(dlg.windowTitle(), "Add Menu Item")
        self.assertTrue(hasattr(dlg, "img_preview"))
        self.assertTrue(hasattr(dlg, "item_field"))


if __name__ == "__main__":
    unittest.main()
