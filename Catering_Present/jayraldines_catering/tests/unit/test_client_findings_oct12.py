import unittest
import os
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import utils.db as db
from utils.sqlite_schema import init_sqlite_db
import utils.repository as repo
import utils.db_sync_server as sync_server
import utils.exporter as exporter


class TestClientFindingsOct12(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_findings.db"
        db.set_sqlite_db_path(self.db_path)
        db.connect_sqlite()

    def tearDown(self):
        try:
            db.close()
            db.set_sqlite_db_path(None)
        except Exception:
            pass
        self.tmp_dir.cleanup()

    def test_finding_1_tablet_sync_ingest_and_resync(self):
        """Verify Finding 1: Tablet booking with motif, menu_type, num_sets, times,
        food sets, and add-ons is ingested accurately into desktop DB, and re-sync updates."""
        tablet_booking = {
            "bk_booking_ref": "TB-TEST-001",
            "bk_customer_name": "Test Client Motif",
            "bk_contact": "09123456789",
            "bk_email": "test@example.com",
            "bk_address": "Cebu City",
            "bk_event_date": "2026-11-20",
            "bk_event_time": "11:00 AM",
            "bk_event_end_time": "3:00 PM",
            "bk_pickup_time": "9:00 AM",
            "bk_dropoff_time": "5:00 PM",
            "bk_venue": "Grand Ballroom",
            "bk_occasion": "Anniversary Gala",
            "bk_pax": 150,
            "bk_num_sets": 3,
            "bk_total_amount": 48500.0,
            "bk_base_total": 45000.0,
            "bk_menu_type": "food_set",
            "bk_color_theme": "Emerald Green",
            "bk_payment_mode": "Cash",
            "bk_amount_paid": 15000.0,
            "bk_down_payment": 15000.0,
            "bk_notes": "VIP Tables",
            "additional_charges": [
                {"description": "Sound System", "amount": 3500.0}
            ],
            "booking_sets": [
                {
                    "set_id": 1,
                    "name": "Set A",
                    "quantity": 2,
                    "unit_price": 15000.0,
                    "dishes": [
                        {"name": "Beef Caldereta", "category": "Beef", "price": 0.0, "quantity": 1},
                        {"name": "Pork Hamonado", "category": "Pork", "price": 0.0, "quantity": 1}
                    ]
                },
                {
                    "set_id": 2,
                    "name": "Set B",
                    "quantity": 1,
                    "unit_price": 15000.0,
                    "dishes": [
                        {"name": "Chicken Curry", "category": "Chicken", "price": 0.0, "quantity": 1}
                    ]
                }
            ]
        }

        # Sync from tablet
        payload = {"bookings": [tablet_booking]}
        response = sync_server.perform_server_sync(payload)
        self.assertIn("TB-TEST-001", response.get("synced_booking_refs", []))

        # Check DB row
        row = db.fetchone("SELECT * FROM bookings WHERE bk_booking_ref = 'TB-TEST-001'")
        self.assertIsNotNone(row)
        self.assertEqual(row["bk_occasion"], "Anniversary Gala")
        self.assertEqual(row["bk_color_theme"], "Emerald Green")
        self.assertEqual(row["bk_menu_type"], "food_set")
        self.assertEqual(row["bk_num_sets"], 3)
        self.assertEqual(row["bk_pickup_time"], "9:00 AM")
        self.assertEqual(row["bk_dropoff_time"], "5:00 PM")
        self.assertEqual(row["bk_base_total"], 45000.0)
        self.assertEqual(row["bk_total_amount"], 48500.0)

        # Check booking_sets
        sets = db.fetchall("SELECT * FROM booking_sets WHERE bs_booking_id = ? ORDER BY bs_sort ASC", (row["bk_id"],))
        self.assertEqual(len(sets), 2)
        self.assertEqual(sets[0]["bs_set_name"], "Set A")
        self.assertEqual(sets[0]["bs_unit_price"], 15000.0)

        # Check booking_additional_charges
        charges = db.fetchall("SELECT * FROM booking_additional_charges WHERE ac_booking_id = ?", (row["bk_id"],))
        self.assertEqual(len(charges), 1)
        self.assertEqual(charges[0]["ac_description"], "Sound System")
        self.assertEqual(charges[0]["ac_amount"], 3500.0)

        # Test re-sync with update (e.g. motif changed, add-on added)
        tablet_booking["bk_color_theme"] = "Royal Navy"
        tablet_booking["additional_charges"].append({"description": "Projector", "amount": 2000.0})
        tablet_booking["bk_total_amount"] = 50500.0
        response2 = sync_server.perform_server_sync({"bookings": [tablet_booking]})
        self.assertIn("TB-TEST-001", response2.get("synced_booking_refs", []))

        row2 = db.fetchone("SELECT * FROM bookings WHERE bk_booking_ref = 'TB-TEST-001'")
        self.assertEqual(row2["bk_color_theme"], "Royal Navy")
        self.assertEqual(row2["bk_total_amount"], 50500.0)
        charges2 = db.fetchall("SELECT * FROM booking_additional_charges WHERE ac_booking_id = ?", (row["bk_id"],))
        self.assertEqual(len(charges2), 2)

    def test_finding_2_base_total_persistence(self):
        """Verify Finding 2: bk_base_total is written and preserved separately from total."""
        b_data = {
            "name": "Jane Doe",
            "contact": "09991112233",
            "email": "jane@example.com",
            "address": "Mandaue City",
            "occasion": "Birthday",
            "venue": "Private Hall",
            "date": "2026-11-25",
            "time": "6:00 PM",
            "pax": 100,
            "menu_type": "package",
            "base_total": 45000.0,
            "total": 52000.0,
            "down_payment": 20000.0,
            "payment_mode": "Cash",
            "additional_charges": [{"description": "Lechon", "amount": 7000.0}]
        }
        res = repo.create_booking(b_data)
        self.assertIsNotNone(res)
        b_id = res.get("p_booking_id")
        self.assertIsNotNone(b_id)

        detail = repo.get_booking_detail(b_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["base_total"], 45000.0)
        self.assertEqual(detail["total_amount"], 52000.0)

    def test_finding_4_order_slip_pdf_exports(self):
        """Verify Finding 4: Kitchen order slip and slips PDF export cleanly via ReportLab."""
        b = {
            "id": "BK-2026-999",
            "booking_ref": "BK-2026-999",
            "name": "Chef Dispatch Test",
            "venue": "Cebu Country Club",
            "event_date": "2026-12-01",
            "event_time": "7:00 PM",
            "pax": 200,
            "package_name": "Standard Buffet Package",
            "motif": "Blush Pink",
            "dishes": [
                {"name": "Pork Belly Roll", "category": "Pork"},
                {"name": "Garlic Butter Chicken", "category": "Chicken"},
                {"name": "Sotanghon Guisado", "category": "Noodles"}
            ],
            "additional_charges": [
                {"description": "Dessert Buffet Bar (₱5,000)"}
            ],
            "notes": "Operations note: handle glassware with care."
        }
        biz = {
            "name": "Jayraldine's Catering",
            "address": "Cebu, Philippines",
            "contact": "Globe: (0945) 9813826 · Landline: 238-9417",
            "email": "jayraldines@gmail.com"
        }

        single_pdf = os.path.join(self.tmp_dir.name, "single_slip.pdf")
        ok1 = exporter.export_order_slip_pdf(single_pdf, b, biz)
        self.assertTrue(ok1)
        self.assertTrue(os.path.exists(single_pdf))
        self.assertGreater(os.path.getsize(single_pdf), 1000)

        multi_pdf = os.path.join(self.tmp_dir.name, "multi_slips.pdf")
        ok2 = exporter.export_order_slips_pdf(multi_pdf, [b, b], biz)
        self.assertTrue(ok2)
        self.assertTrue(os.path.exists(multi_pdf))
        self.assertGreater(os.path.getsize(multi_pdf), 1000)

    def test_delete_sync_child_items_reconciliation(self):
        """Verify Gap B: Removing child dishes/sets and add-ons on an already-synced
        booking accurately reconciles and deletes them from desktop DB."""
        booking = {
            "bk_booking_ref": "TB-DEL-001",
            "bk_customer_name": "Delete Child Test",
            "bk_event_date": "2026-11-28",
            "bk_event_time": "12:00 PM",
            "bk_venue": "Function Room",
            "bk_total_amount": 35000.0,
            "additional_charges": [
                {"description": "Addon 1", "amount": 2500.0},
                {"description": "Addon 2", "amount": 1500.0}
            ],
            "booking_sets": [
                {
                    "set_id": 1,
                    "name": "Set 1",
                    "quantity": 1,
                    "unit_price": 15000.0,
                    "dishes": [{"name": "Dish A", "category": "Pork", "price": 0.0, "quantity": 1}]
                },
                {
                    "set_id": 2,
                    "name": "Set 2",
                    "quantity": 1,
                    "unit_price": 15000.0,
                    "dishes": [{"name": "Dish B", "category": "Beef", "price": 0.0, "quantity": 1}]
                }
            ]
        }
        resp = sync_server.perform_server_sync({"bookings": [booking]})
        self.assertIn("TB-DEL-001", resp.get("synced_booking_refs", []))
        bk = db.fetchone("SELECT bk_id FROM bookings WHERE bk_booking_ref = 'TB-DEL-001'")
        self.assertIsNotNone(bk)
        bkid = bk["bk_id"]

        charges = db.fetchall("SELECT * FROM booking_additional_charges WHERE ac_booking_id = ?", (bkid,))
        sets = db.fetchall("SELECT * FROM booking_sets WHERE bs_booking_id = ?", (bkid,))
        self.assertEqual(len(charges), 2)
        self.assertEqual(len(sets), 2)

        # Now simulate tablet editing the booking: removing 1 food set and removing ALL add-ons
        booking["additional_charges"] = []
        booking["booking_sets"] = [
            {
                "set_id": 1,
                "name": "Set 1",
                "quantity": 1,
                "unit_price": 15000.0,
                "dishes": [{"name": "Dish A", "category": "Pork", "price": 0.0, "quantity": 1}]
            }
        ]
        booking["bk_total_amount"] = 15000.0

        resp2 = sync_server.perform_server_sync({"bookings": [booking]})
        self.assertIn("TB-DEL-001", resp2.get("synced_booking_refs", []))

        # Check that charges are now 0 and sets are now 1
        charges2 = db.fetchall("SELECT * FROM booking_additional_charges WHERE ac_booking_id = ?", (bkid,))
        sets2 = db.fetchall("SELECT * FROM booking_sets WHERE bs_booking_id = ?", (bkid,))
        self.assertEqual(len(charges2), 0)
        self.assertEqual(len(sets2), 1)
        self.assertEqual(sets2[0]["bs_set_name"], "Set 1")

    def test_delete_sync_tablet_to_desktop_entities(self):
        """Verify Gap A: Deleting customers, packages, menu items, and occasions
        on the tablet propagates deletions and prevents resurrection."""
        # 1. Create a customer
        db.execute("INSERT INTO customers (cus_name, cus_contact) VALUES ('Customer To Delete', '09120000000')")
        c_row = db.fetchone("SELECT cus_id FROM customers WHERE cus_name = 'Customer To Delete'")
        self.assertIsNotNone(c_row)
        cid = c_row["cus_id"]

        # 2. Create a package
        db.execute("INSERT INTO packages (pkg_name, pkg_price_per_pax) VALUES ('Package To Delete', 350.0)")
        p_row = db.fetchone("SELECT pkg_id FROM packages WHERE pkg_name = 'Package To Delete'")
        self.assertIsNotNone(p_row)
        pid = p_row["pkg_id"]

        # 3. Create a menu item
        db.execute("INSERT INTO menu_items (mi_name, mi_category, mi_price) VALUES ('Dish To Delete', 'Dessert', 150.0)")
        m_row = db.fetchone("SELECT mi_id FROM menu_items WHERE mi_name = 'Dish To Delete'")
        self.assertIsNotNone(m_row)
        mid = m_row["mi_id"]

        # 4. Create an occasion
        db.execute("INSERT INTO occasions (occ_name) VALUES ('Occasion To Delete')")
        o_row = db.fetchone("SELECT occ_id FROM occasions WHERE occ_name = 'Occasion To Delete'")
        self.assertIsNotNone(o_row)

        # Sync deletion payload from tablet
        del_payload = {
            "deleted_customer_ids": [cid],
            "deleted_package_ids": [pid],
            "deleted_menu_item_ids": [mid],
            "deleted_occasion_names": ["Occasion To Delete"]
        }
        res = sync_server.perform_server_sync(del_payload)
        self.assertTrue(res.get("deleted_customer_ids_handled"))
        self.assertTrue(res.get("deleted_package_ids_handled"))
        self.assertTrue(res.get("deleted_menu_item_ids_handled"))
        self.assertTrue(res.get("deleted_occasion_ids_handled"))

        # Check that rows are gone from DB
        self.assertIsNone(db.fetchone("SELECT cus_id FROM customers WHERE cus_id = ?", (cid,)))
        self.assertIsNone(db.fetchone("SELECT pkg_id FROM packages WHERE pkg_id = ?", (pid,)))
        self.assertIsNone(db.fetchone("SELECT mi_id FROM menu_items WHERE mi_id = ?", (mid,)))
        self.assertIsNone(db.fetchone("SELECT occ_id FROM occasions WHERE occ_name = 'Occasion To Delete'"))

        # Check resurrection guard: tablet trying to push deleted customer again is blocked
        res2 = sync_server.perform_server_sync({
            "customers": [{"cus_id": cid, "cus_name": "Customer To Delete", "cus_contact": "09120000000"}]
        })
        self.assertIsNone(db.fetchone("SELECT cus_id FROM customers WHERE cus_id = ?", (cid,)))


if __name__ == "__main__":
    unittest.main()

