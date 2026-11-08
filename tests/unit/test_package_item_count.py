import unittest

def validate_package_counts(mains, desserts, drinks, min_mains=3):
    return len(mains) >= min_mains and len(desserts) >= 1 and len(drinks) >= 1

class TestPackageItemCount(unittest.TestCase):
    def test_valid_package_item_selection(self):
        mains = ["Beef Caldereta", "Sweet & Sour Pork", "Chicken Cordon Bleu"]
        desserts = ["Mango Float"]
        drinks = ["Iced Tea"]
        self.assertTrue(validate_package_counts(mains, desserts, drinks))

    def test_insufficient_mains_fails(self):
        mains = ["Beef Caldereta"]
        desserts = ["Mango Float"]
        drinks = ["Iced Tea"]
        self.assertFalse(validate_package_counts(mains, desserts, drinks))

if __name__ == "__main__":
    unittest.main()
