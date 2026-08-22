import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import utils.repository as repo
import utils.importer as importer


class TestFixes(unittest.TestCase):

    def test_parse_date_robustness(self):
        """Test _parse_date handles date, datetime, string formats, and invalid inputs."""
        today = date.today()
        self.assertEqual(repo._parse_date(today), today)
        self.assertEqual(repo._parse_date(datetime(2026, 8, 20, 10, 30)), date(2026, 8, 20))
        self.assertEqual(repo._parse_date("Aug 20, 2026"), date(2026, 8, 20))
        self.assertEqual(repo._parse_date("2026-08-20"), date(2026, 8, 20))
        self.assertEqual(repo._parse_date("08/20/2026"), date(2026, 8, 20))
        self.assertEqual(repo._parse_date("August 20, 2026"), date(2026, 8, 20))
        # Empty or None should fallback to today safely without crashing
        self.assertEqual(repo._parse_date(None), today)
        self.assertEqual(repo._parse_date(""), today)

    def test_search_cebu_address_multi_token(self):
        """Test search_cebu_address handles multi-token searches like 'Mabolo Cebu'."""
        sample_cache = [
            {"barangay_id": 1, "barangay": "Mabolo", "city": "Cebu City", "province": "Cebu", "display_text": "Mabolo, Cebu City, Cebu"},
            {"barangay_id": 2, "barangay": "Lahug", "city": "Cebu City", "province": "Cebu", "display_text": "Lahug, Cebu City, Cebu"},
            {"barangay_id": 3, "barangay": "Guadalupe", "city": "Cebu City", "province": "Cebu", "display_text": "Guadalupe, Cebu City, Cebu"},
            {"barangay_id": 4, "barangay": "Bakilid", "city": "Mandaue City", "province": "Cebu", "display_text": "Bakilid, Mandaue City, Cebu"},
        ]
        with patch.object(repo, "get_all_cebu_addresses", return_value=sample_cache):
            # Exact prefix match
            res1 = repo.search_cebu_address("Mabolo")
            self.assertTrue(any(r["barangay"] == "Mabolo" for r in res1))

            # Multi-token match
            res2 = repo.search_cebu_address("Mabolo Cebu")
            self.assertTrue(any(r["barangay"] == "Mabolo" for r in res2))

            # City + Barangay token match
            res3 = repo.search_cebu_address("Lahug Cebu City")
            self.assertTrue(any(r["barangay"] == "Lahug" for r in res3))

    @patch("utils.db.fetchall")
    def test_get_calendar_events_for_month_batch(self, mock_fetchall):
        """Test get_calendar_events_for_month groups events by (year, month, day)."""
        mock_fetchall.side_effect = [
            # Bookings query
            [
                {
                    "event_date": date(2026, 8, 15),
                    "booking_ref": "BK-001",
                    "customer_name": "John Doe",
                    "pax": 100,
                    "event_time": datetime.strptime("18:00", "%H:%M").time(),
                    "venue": "Cebu Ballroom",
                    "occasion": "Wedding",
                    "status": "CONFIRMED",
                }
            ],
            # Calendar events query
            [
                {
                    "event_date": date(2026, 8, 15),
                    "id": 10,
                    "name": "Food Tasting",
                    "pax": 4,
                    "event_time": "02:00 PM",
                    "location": "Main Kitchen",
                }
            ]
        ]
        result = repo.get_calendar_events_for_month(2026, 8)
        self.assertIn((2026, 8, 15), result)
        self.assertEqual(len(result[(2026, 8, 15)]), 2)
        self.assertEqual(result[(2026, 8, 15)][0]["ref"], "BK-001")
        self.assertEqual(result[(2026, 8, 15)][1]["name"], "Food Tasting")

    @patch("utils.repository.add_customer")
    @patch("utils.repository.create_booking")
    @patch("utils.repository.add_expense")
    def test_importer_all_in_one_execution(self, mock_add_exp, mock_create_bkg, mock_add_cust):
        """Test execute_batch_import handles all_in_one entity type properly."""
        mock_add_cust.return_value = 1
        mock_create_bkg.return_value = {"booking_id": 1}
        mock_add_exp.return_value = 1

        prepared = [{
            "_row_index": 1,
            "_status": "valid",
            "_issues": [],
            "_data": {
                "customer_name": "Maria Santos",
                "contact": "09171234567",
                "email": "maria@example.com",
                "event_date": "Aug 20, 2026",
                "venue": "Ballroom",
                "occasion": "Wedding",
                "pax": 150,
                "total_amount": 45000.0,
                "expense_date": "Aug 20, 2026",
                "expense_category": "Food Cost",
                "expense_description": "Pork Lechon",
                "expense_amount": 15500.0,
            }
        }]

        s_cnt, f_cnt, errors = importer.execute_batch_import(prepared, "all_in_one")
        self.assertEqual(s_cnt, 1)
        self.assertEqual(f_cnt, 0)
        self.assertEqual(len(errors), 0)
        mock_add_cust.assert_called_once()
        mock_create_bkg.assert_called_once()
        mock_add_exp.assert_called_once()


if __name__ == "__main__":
    unittest.main()
