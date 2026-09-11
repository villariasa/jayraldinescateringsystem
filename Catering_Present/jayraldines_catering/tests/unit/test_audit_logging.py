import unittest
from datetime import date, datetime
import utils.repository as repo
from utils.session import set_actor, get_actor


class TestAuditLogging(unittest.TestCase):
    def setUp(self):
        set_actor("TestAdmin")

    def test_format_audit_description_customer(self):
        """Test _format_audit_description produces informative customer descriptions."""
        # Create
        desc_create = repo._format_audit_description(
            "CREATE",
            None,
            {"name": "Juan Dela Cruz", "contact": "09171234567", "email": "juan@test.com", "address": "Cebu City"},
            table_name="customers"
        )
        self.assertIn("Added new customer", desc_create)
        self.assertIn("Juan Dela Cruz", desc_create)
        self.assertIn("09171234567", desc_create)

        # Update
        desc_update = repo._format_audit_description(
            "UPDATE",
            None,
            {"name": "Juan Dela Cruz", "contact": "09189999999"},
            table_name="customers"
        )
        self.assertIn("Updated customer details", desc_update)
        self.assertIn("Juan Dela Cruz", desc_update)

        # Delete
        desc_del = repo._format_audit_description(
            "DELETE",
            {"name": "Juan Dela Cruz"},
            None,
            table_name="customers"
        )
        self.assertIn("Deleted customer", desc_del)
        self.assertIn("Juan Dela Cruz", desc_del)

    def test_format_audit_description_other_entities(self):
        """Test _format_audit_description handles menu items, packages, expenses, and payments."""
        # Menu item
        desc_mi = repo._format_audit_description(
            "CREATE",
            None,
            {"name": "Lechon Belly", "category": "Pork", "price": 450},
            table_name="menu_items"
        )
        self.assertIn("Added menu item", desc_mi)
        self.assertIn("Lechon Belly", desc_mi)

        # Package
        desc_pkg = repo._format_audit_description(
            "CREATE",
            None,
            {"name": "Wedding Deluxe", "price_per_head": 550},
            table_name="packages"
        )
        self.assertIn("Added package", desc_pkg)
        self.assertIn("Wedding Deluxe", desc_pkg)

        # Expense
        desc_exp = repo._format_audit_description(
            "CREATE",
            None,
            {"description": "Cooking Oil & Charcoal", "amount": 1200, "category": "Supplies"},
            table_name="expenses"
        )
        self.assertIn("expense", desc_exp.lower())
        self.assertIn("Cooking Oil & Charcoal", desc_exp)

        # Payment
        desc_pay = repo._format_audit_description(
            "PAYMENT",
            None,
            {"customer": "Maria Clara", "amount": 15000, "method": "GCash"},
            table_name="invoices"
        )
        self.assertIn("payment", desc_pay.lower())
        self.assertIn("Maria Clara", desc_pay)
        self.assertIn("15,000.00", desc_pay)

    def test_customer_crud_audit_logging(self):
        """Test that customer add, update, and delete all generate audit logs."""
        unique_name = f"AuditTest_Customer_{int(datetime.now().timestamp())}"
        
        # 1. ADD
        cust_data = {
            "name": unique_name,
            "contact": "09991112222",
            "email": "audittest@example.com",
            "address": "Banilad, Cebu City",
            "notes": "VIP Client",
            "occasion_preference": "Wedding",
            "status": "ACTIVE",
        }
        res = repo.add_customer(cust_data)
        self.assertIsNotNone(res)
        cust_id = res.get("id") if isinstance(res, dict) else res

        # Verify CREATE log entry
        logs = repo.get_audit_log(limit=10, table_name="customers")
        add_logs = [l for l in logs if unique_name in l.get("description", "") and l.get("action") == "CREATE"]
        self.assertTrue(len(add_logs) >= 1, f"Expected CREATE audit log for {unique_name}, got {logs}")
        self.assertEqual(add_logs[0]["actor"], "TestAdmin")
        self.assertIn(unique_name, add_logs[0]["description"])

        # 2. UPDATE
        updated_name = f"{unique_name}_Updated"
        cust_data["name"] = updated_name
        cust_data["contact"] = "09993334444"
        repo.update_customer(cust_id, cust_data)

        logs_upd = repo.get_audit_log(limit=10, table_name="customers")
        upd_logs = [l for l in logs_upd if updated_name in l.get("description", "") and l.get("action") == "UPDATE"]
        self.assertTrue(len(upd_logs) >= 1, f"Expected UPDATE audit log for {updated_name}")

        # 3. DELETE
        repo.delete_customer(cust_id)
        logs_del = repo.get_audit_log(limit=10, table_name="customers")
        del_logs = [l for l in logs_del if updated_name in l.get("description", "") and l.get("action") == "DELETE"]
        self.assertTrue(len(del_logs) >= 1, f"Expected DELETE audit log for {updated_name}")

    def test_menu_item_crud_audit_logging(self):
        """Test that menu item add and delete generate audit logs."""
        m_name = f"Item_{int(datetime.now().timestamp())}"
        item_id = repo.add_menu_item({
            "name": m_name,
            "category": "Main Course",
            "package": "Standard",
            "price": 350.0,
            "status": "Available",
        })
        self.assertIsNotNone(item_id)

        logs = repo.get_audit_log(limit=10, table_name="menu_items")
        create_logs = [l for l in logs if m_name in l.get("description", "") and l.get("action") == "CREATE"]
        self.assertTrue(len(create_logs) >= 1, f"Expected CREATE audit log for menu item {m_name}")

        # Delete
        repo.delete_menu_item(item_id)
        logs_del = repo.get_audit_log(limit=10, table_name="menu_items")
        del_logs = [l for l in logs_del if m_name in l.get("description", "") and l.get("action") == "DELETE"]
        self.assertTrue(len(del_logs) >= 1, f"Expected DELETE audit log for menu item {m_name}")

    def test_expense_crud_audit_logging(self):
        """Test that expense add and delete generate audit logs."""
        unique_desc = f"Expense_{int(datetime.now().timestamp())}"
        exp_id = repo.add_expense({
            "category": "Supplies",
            "description": unique_desc,
            "amount": 750.0,
            "date": date.today().isoformat(),
        })
        self.assertIsNotNone(exp_id)

        logs = repo.get_audit_log(limit=10, table_name="expenses")
        create_logs = [l for l in logs if unique_desc in l.get("description", "") and l.get("action") == "CREATE"]
        self.assertTrue(len(create_logs) >= 1, f"Expected CREATE audit log for expense {unique_desc}")

        # Delete
        repo.delete_expense(exp_id)
        logs_del = repo.get_audit_log(limit=10, table_name="expenses")
        del_logs = [l for l in logs_del if unique_desc in l.get("description", "") and l.get("action") == "DELETE"]
        self.assertTrue(len(del_logs) >= 1, f"Expected DELETE audit log for expense {unique_desc}")

    def test_daily_activity_report_data_and_pdf(self):
        """Test that get_audit_log supports date filtering and exporter generates report."""
        import utils.exporter as exporter
        import tempfile
        import os

        today_str = date.today().strftime("%Y-%m-%d")
        entries = repo.get_audit_log(start_date=today_str, end_date=today_str)
        self.assertIsInstance(entries, list)
        self.assertTrue(len(entries) > 0, "Expected today's audit log entries")

        # Check entry fields
        sample = entries[0]
        self.assertIn("date", sample)
        self.assertIn("time", sample)
        self.assertIn("actor", sample)
        self.assertIn("action", sample)
        self.assertIn("description", sample)

        # Test PDF exporter
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        try:
            biz = repo.get_business_info() or {"name": "Jayraldine's Catering"}
            ok = exporter.export_daily_activity_report_pdf(tmp.name, entries, biz, period_label="Today")
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(tmp.name))
            self.assertGreater(os.path.getsize(tmp.name), 1000)
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)


if __name__ == "__main__":
    unittest.main()
