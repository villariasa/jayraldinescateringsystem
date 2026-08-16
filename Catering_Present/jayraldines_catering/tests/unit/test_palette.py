import unittest
from utils.palette import THEME_CATEGORIES, THEME_PALETTES, get_palettes_by_category, get_palette
from utils.theme import ThemeManager


class TestThemePaletteSystem(unittest.TestCase):
    def test_all_categories_present(self):
        expected_cats = [
            "Mood/Tone-based",
            "Nature-inspired",
            "Color-driven",
            "Vibe-based",
            "Seasonal"
        ]
        for cat in expected_cats:
            self.assertIn(cat, THEME_CATEGORIES)

    def test_palettes_have_required_keys(self):
        required_keys = ["id", "name", "category", "mode", "primary", "background", "surface", "text_primary", "border"]
        for pid, pal in THEME_PALETTES.items():
            for key in required_keys:
                self.assertIn(key, pal, f"Palette {pid} is missing key {key}")
            self.assertIn(pal["mode"], ["dark", "light"])
            self.assertIn(pal["category"], THEME_CATEGORIES)

    def test_get_palettes_by_category(self):
        grouped = get_palettes_by_category()
        for cat in THEME_CATEGORIES:
            self.assertIn(cat, grouped)
            self.assertGreater(len(grouped[cat]), 0, f"Category {cat} should have at least one palette")

    def test_fallback_palette(self):
        pal = get_palette("non_existent_palette_id")
        self.assertEqual(pal["id"], "dark_mode")


if __name__ == "__main__":
    unittest.main()
