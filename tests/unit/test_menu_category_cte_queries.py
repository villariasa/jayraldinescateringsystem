import unittest

class TestMenuCategoryCteQueries(unittest.TestCase):
    def test_cte_query_structure(self):
        query = "WITH RECURSIVE CategoryTree AS (SELECT mc_id FROM menu_categories) SELECT * FROM CategoryTree;"
        self.assertTrue(query.startswith("WITH RECURSIVE"))
        self.assertIn("CategoryTree", query)

if __name__ == "__main__":
    unittest.main()
