import os
import shutil
import tempfile
import unittest
from pathlib import Path

from utils.db_config import (
    generate_random_password,
    get_local_lan_ip,
    save_db_config,
    load_db_config,
    get_db_config,
)
from utils.auth import (
    validate_password,
    hash_password,
    verify_password,
    ensure_auth_tables,
    create_default_admin,
    create_user,
    authenticate,
    update_user_password,
    update_user_permissions,
    set_user_active,
    list_users,
    SessionManager,
)
import utils.db as db


class TestAuthAndConfig(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_auth.db"
        db.set_sqlite_db_path(self.db_path)
        db.connect_sqlite()

    def tearDown(self):
        db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_password_generation(self):
        pwd = generate_random_password(16)
        self.assertEqual(len(pwd), 16)
        is_valid, err = validate_password(pwd)
        self.assertTrue(is_valid, f"Generated password failed validation: {err}")

    def test_password_complexity(self):
        self.assertFalse(validate_password("short")[0])
        self.assertFalse(validate_password("onlyletters")[0])
        self.assertFalse(validate_password("12345678")[0])
        self.assertTrue(validate_password("Valid1234")[0])

    def test_password_hashing(self):
        pwd = "MySecretPassword123!"
        h = hash_password(pwd)
        self.assertTrue(h.startswith("pbkdf2:sha256:100000$"))
        self.assertTrue(verify_password(pwd, h))
        self.assertFalse(verify_password("WrongPassword123!", h))

    def test_lan_ip_detection(self):
        ip = get_local_lan_ip()
        self.assertIsInstance(ip, str)
        self.assertEqual(len(ip.split(".")), 4)

    def test_auth_sqlite_flow(self):
        ensure_auth_tables()

        # 1. Create default admin
        admin_user, admin_pass = create_default_admin("AdminSecret123!")
        self.assertEqual(admin_user, "admin")
        self.assertEqual(admin_pass, "AdminSecret123!")

        # Second call should not overwrite
        u2, p2 = create_default_admin()
        self.assertEqual(p2, "")

        # 2. Authenticate admin
        admin_data = authenticate("admin", "AdminSecret123!")
        self.assertIsNotNone(admin_data)
        self.assertEqual(admin_data["role"], "admin")
        self.assertTrue(admin_data["permissions"]["customers"]["view"])
        self.assertTrue(admin_data["permissions"]["cashflow"]["delete"])

        # 3. Create staff user
        ok, msg, user_id = create_user("cashier1", "CashierPass123", "Maria Cashier", role="staff")
        self.assertTrue(ok)
        self.assertIsNotNone(user_id)

        # Authenticate staff
        staff_data = authenticate("cashier1", "CashierPass123")
        self.assertIsNotNone(staff_data)
        self.assertEqual(staff_data["role"], "staff")
        self.assertTrue(staff_data["permissions"]["customers"]["view"])
        self.assertFalse(staff_data["permissions"]["cashflow"]["view"])

        # 4. Update staff permissions
        perms = staff_data["permissions"]
        perms["cashflow"]["view"] = True
        perms["cashflow"]["create"] = True
        self.assertTrue(update_user_permissions(user_id, perms))

        # Re-verify permissions
        staff_data2 = authenticate("cashier1", "CashierPass123")
        self.assertTrue(staff_data2["permissions"]["cashflow"]["view"])

        # 5. SessionManager tests
        SessionManager.set_user(staff_data2)
        self.assertTrue(SessionManager.is_logged_in())
        self.assertFalse(SessionManager.is_admin())
        self.assertTrue(SessionManager.has_permission("cashflow", "view"))
        self.assertFalse(SessionManager.has_permission("cashflow", "delete"))

        # Switch to admin in SessionManager
        SessionManager.set_user(admin_data)
        self.assertTrue(SessionManager.is_admin())
        self.assertTrue(SessionManager.has_permission("any_module", "delete"))

        SessionManager.logout()
        self.assertFalse(SessionManager.is_logged_in())

        # 6. Deactivate staff
        ok, msg = set_user_active(user_id, False)
        self.assertTrue(ok)
        self.assertIsNone(authenticate("cashier1", "CashierPass123"))

        # Cannot deactivate admin
        ok, msg = set_user_active(1, False)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
