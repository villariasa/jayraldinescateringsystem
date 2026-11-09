import unittest

def calculate_raw_ingredient_kg(portion_grams_per_pax, guest_count, buffer_pct=0.10):
    total_grams = portion_grams_per_pax * guest_count * (1.0 + buffer_pct)
    return round(total_grams / 1000.0, 2)

class TestFoodPortionMultiplier(unittest.TestCase):
    def test_beef_caldereta_batch(self):
        # 150g beef per pax for 100 guests with 10% buffer = 16.5 kg
        self.assertEqual(calculate_raw_ingredient_kg(150, 100), 16.5)

    def test_dessert_portion_batch(self):
        # 80g mango float per pax for 50 guests with 10% buffer = 4.4 kg
        self.assertEqual(calculate_raw_ingredient_kg(80, 50), 4.4)

if __name__ == "__main__":
    unittest.main()
