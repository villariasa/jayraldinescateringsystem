import unittest

class TestDessertPortionScaling(unittest.TestCase):
    def test_pastry_headcount_multiplier(self):
        guest_count = 150
        pieces_per_guest = 2.5
        total_pieces = int(guest_count * pieces_per_guest)
        self.assertEqual(total_pieces, 375)

    def test_cake_slice_buffer_percentage(self):
        standard_slices = 100
        buffer_percent = 0.10
        total_prepared = int(standard_slices * (1 + buffer_percent))
        self.assertEqual(total_prepared, 110)

if __name__ == '__main__':
    unittest.main()
