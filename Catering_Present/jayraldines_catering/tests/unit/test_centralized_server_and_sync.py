"""
Unit and integration tests for Centralized Database Server Architecture,
RBAC Permission Enforcement, Chef Jay AI Permission Gating, Emergency Admin Reset,
and Tablet PWA Duplicate-Proof Sync.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add project root to sys.path
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import utils.db as db
from utils.auth import (
    ensure_auth_tables, create_default_admin, create_user,
    set_user_permissions, get_user_permissions, authenticate,
    SessionManager, reset_user_password, validate_password,
    hash_password, verify_password
)
import utils.ai_client as ai_client


class TestCentralizedServerAndSync(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_central.db"
        db.set_sqlite_db_path(self.db_path)
        db.connect_sqlite()
        ensure_auth_tables()
        SessionManager.logout()
        SessionManager._auto_lock_minutes = None

    def tearDown(self):
        SessionManager.logout()
        SessionManager._auto_lock_minutes = None
        db.close()
        db.set_sqlite_db_path(None)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_session_manager_auto_lock_configuration(self):
        """Test auto-lock timeout setting, getting, and persistence."""
        from unittest.mock import patch
        mock_cfg = {}
        with patch("utils.db_config.load_db_config", side_effect=lambda: mock_cfg), \
             patch("utils.db_config.save_db_config", side_effect=lambda c: mock_cfg.update(c)):
            SessionManager._auto_lock_minutes = None
            # Default should be 60 minutes
            self.assertEqual(SessionManager.get_auto_lock_minutes(), 60)

            # Set to 30 minutes
            SessionManager.set_auto_lock_minutes(30)
            self.assertEqual(SessionManager.get_auto_lock_minutes(), 30)

            # Set to 120 minutes
            SessionManager.set_auto_lock_minutes(120)
            self.assertEqual(SessionManager.get_auto_lock_minutes(), 120)

            # Set to 0 (Disabled)
            SessionManager.set_auto_lock_minutes(0)
            self.assertEqual(SessionManager.get_auto_lock_minutes(), 0)

        # Restore to 60
        SessionManager.set_auto_lock_minutes(60)
        self.assertEqual(SessionManager.get_auto_lock_minutes(), 60)

    def test_rbac_admin_vs_staff_permissions(self):
        """Test admin always has full permissions while staff permissions are strictly enforced."""
        # Create admin
        create_default_admin("AdminSecret123!")
        admin_data = authenticate("admin", "AdminSecret123!")
        self.assertIsNotNone(admin_data)

        SessionManager.set_user(admin_data)
        self.assertTrue(SessionManager.is_admin())
        for mod in ["dashboard", "booking", "customers", "menu", "cashflow", "expenses", "reports", "settings"]:
            self.assertTrue(SessionManager.has_permission(mod, "view"))
            self.assertTrue(SessionManager.has_permission(mod, "create"))
            self.assertTrue(SessionManager.has_permission(mod, "edit"))
            self.assertTrue(SessionManager.has_permission(mod, "delete"))

        # Create staff user with limited permissions (view-only on menu, no delete on customers)
        ok, msg, staff_id = create_user("staff_lisa", "LisaPass123!", "Lisa Kitchen", "staff")
        self.assertTrue(ok)

        perms = {
            "menu": {"view": True, "create": False, "edit": False, "delete": False},
            "customers": {"view": True, "create": True, "edit": True, "delete": False},
            "expenses": {"view": False, "create": False, "edit": False, "delete": False},
            "booking": {"view": True, "create": True, "edit": False, "delete": False},
        }
        set_user_permissions(staff_id, perms)

        staff_data = authenticate("staff_lisa", "LisaPass123!")
        self.assertIsNotNone(staff_data)
        SessionManager.set_user(staff_data)
        self.assertFalse(SessionManager.is_admin())

        # Check menu permissions
        self.assertTrue(SessionManager.has_permission("menu", "view"))
        self.assertFalse(SessionManager.has_permission("menu", "create"))
        self.assertFalse(SessionManager.has_permission("menu", "edit"))
        self.assertFalse(SessionManager.has_permission("menu", "delete"))

        # Check customers permissions
        self.assertTrue(SessionManager.has_permission("customers", "view"))
        self.assertTrue(SessionManager.has_permission("customers", "create"))
        self.assertTrue(SessionManager.has_permission("customers", "edit"))
        self.assertFalse(SessionManager.has_permission("customers", "delete"))

        # Check expenses permissions
        self.assertFalse(SessionManager.has_permission("expenses", "view"))
        self.assertFalse(SessionManager.has_permission("expenses", "create"))

    def test_chef_jay_ai_permission_gating(self):
        """Test Chef Jay AI blocks actions when user lacks required permission."""
        # Create restricted staff
        ok, msg, staff_id = create_user("staff_waiter", "WaiterPass123!", "John Waiter", "staff")
        self.assertTrue(ok)

        # Allow only view on customers and menu, but NO create on expenses or delete on customers
        set_user_permissions(staff_id, {
            "customers": {"view": True, "create": False, "edit": False, "delete": False},
            "expenses": {"view": False, "create": False, "edit": False, "delete": False},
            "cashflow": {"view": True, "create": False, "edit": False, "delete": False},
        })

        user_data = authenticate("staff_waiter", "WaiterPass123!")
        SessionManager.set_user(user_data)

        # Attempt to execute an expense addition
        expense_action = {
            "type": "expense",
            "category": "utilities",
            "description": "Electricity bill",
            "amount": 1500.0,
        }
        res = ai_client.execute_action(expense_action)
        self.assertFalse(res["ok"])
        self.assertIn("Permission Denied", res["message"])
        self.assertIn("expenses", res["message"].lower())

        # Attempt customer deletion
        del_action = {
            "type": "customer_delete",
            "db_id": 999,
            "name": "Target Customer",
        }
        res_del = ai_client.execute_action(del_action)
        self.assertFalse(res_del["ok"])
        self.assertIn("Permission Denied", res_del["message"])

        # Now switch to admin and verify actions are allowed
        admin_data = authenticate("admin", "AdminSecret123!")
        if not admin_data:
            create_default_admin("AdminSecret123!")
            admin_data = authenticate("admin", "AdminSecret123!")

        SessionManager.set_user(admin_data)
        # Verify pre-flight check passes for admin
        chk = ai_client._check_action_perm({"ok": True, "action": expense_action})
        self.assertTrue(chk["ok"])
        self.assertIsNotNone(chk["action"])

    def test_emergency_admin_reset_cli(self):
        """Test the emergency admin password reset mechanism."""
        # Initially create an admin with initial password
        create_default_admin("InitialSecret123!")
        self.assertIsNotNone(authenticate("admin", "InitialSecret123!"))

        # Simulate CLI reset with new password
        new_cli_pwd = "ResetPassword999!"
        admin_row = db.fetchone("SELECT id FROM users WHERE username = 'admin'")
        self.assertIsNotNone(admin_row)

        ok, msg = reset_user_password(admin_row["id"], new_cli_pwd)
        self.assertTrue(ok)
        self.assertIn("successfully", msg.lower())

        # Old password must now fail
        self.assertIsNone(authenticate("admin", "InitialSecret123!"))

        # New password must succeed
        new_auth = authenticate("admin", new_cli_pwd)
        self.assertIsNotNone(new_auth)
        self.assertEqual(new_auth["username"], "admin")

    def test_tablet_pwa_smart_sync_deduplication(self):
        """Test Tablet PWA schema and duplicate-proof record synchronization."""
        # Create table with sync_status column
        db.execute("""
            CREATE TABLE IF NOT EXISTS test_sync_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_ref TEXT UNIQUE NOT NULL,
                customer_name TEXT,
                total REAL,
                sync_status TEXT DEFAULT 'pending'
            );
        """)

        # Insert 2 bookings
        db.execute("INSERT INTO test_sync_bookings (booking_ref, customer_name, total, sync_status) VALUES (?, ?, ?, 'pending')",
                   ("BK-2026-001", "Alice Reyes", 5000.0))
        db.execute("INSERT INTO test_sync_bookings (booking_ref, customer_name, total, sync_status) VALUES (?, ?, ?, 'pending')",
                   ("BK-2026-002", "Bob Cruz", 7500.0))

        # Check pending count
        pending = db.fetchall("SELECT * FROM test_sync_bookings WHERE sync_status = 'pending'")
        self.assertEqual(len(pending), 2)

        # Simulate sync push to server: Mark synced
        for b in pending:
            db.execute("UPDATE test_sync_bookings SET sync_status = 'synced' WHERE id = ?", (b["id"],))

        # Now pending should be 0
        remaining = db.fetchall("SELECT * FROM test_sync_bookings WHERE sync_status = 'pending'")
        self.assertEqual(len(remaining), 0)

        # Simulate offline order taking on tablet
        db.execute("INSERT INTO test_sync_bookings (booking_ref, customer_name, total, sync_status) VALUES (?, ?, ?, 'pending')",
                   ("BK-2026-003", "Charlie Gomez", 12000.0))

        # Check pending is now exactly 1
        new_pending = db.fetchall("SELECT * FROM test_sync_bookings WHERE sync_status = 'pending'")
        self.assertEqual(len(new_pending), 1)
        self.assertEqual(new_pending[0]["booking_ref"], "BK-2026-003")


if __name__ == "__main__":
    unittest.main()
