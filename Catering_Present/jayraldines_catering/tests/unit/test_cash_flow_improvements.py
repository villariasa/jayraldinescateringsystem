import sys
import unittest
from datetime import datetime
from PySide6.QtWidgets import QApplication

import utils.repository as repo
from ui.cash_flow_page import CashFlowPage, TransactionModal, _DEFAULT_PARTICULARS


class TestCashFlowImprovements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        # Clean up test rows
        repo.db.execute("DELETE FROM cash_flow_transactions WHERE cft_check_no LIKE 'TEST-CF-%'")
        repo.recalculate_cash_flow_balances()

    def tearDown(self):
        repo.db.execute("DELETE FROM cash_flow_transactions WHERE cft_check_no LIKE 'TEST-CF-%'")
        repo.recalculate_cash_flow_balances()

    def test_bdo_savings_removed(self):
        """Verify 'BDO Personal Savings (SAVINGS)' is completely removed from particulars list and classification balances."""
        self.assertNotIn("BDO Personal Savings (SAVINGS)", _DEFAULT_PARTICULARS)
        balances = repo.get_cash_flow_classification_balances()
        self.assertNotIn("BDO Personal Savings (SAVINGS)", balances)

    def test_newest_entries_on_top(self):
        """Verify newly entered cash flow transactions appear at the top row (ORDER BY date DESC, id DESC)."""
        # Insert older transaction
        id1 = repo.add_cash_flow_transaction({
            "date": "2026-01-01",
            "check_no": "TEST-CF-001",
            "particulars": "GCash",
            "deposit": 1000.0,
            "withdrawal": 0.0,
            "notes": "First transaction"
        })
        # Insert newer transaction
        id2 = repo.add_cash_flow_transaction({
            "date": "2026-02-01",
            "check_no": "TEST-CF-002",
            "particulars": "GCash",
            "deposit": 2000.0,
            "withdrawal": 0.0,
            "notes": "Second transaction"
        })
        # Insert newest transaction
        id3 = repo.add_cash_flow_transaction({
            "date": "2026-03-01",
            "check_no": "TEST-CF-003",
            "particulars": "GCash",
            "deposit": 500.0,
            "withdrawal": 0.0,
            "notes": "Third transaction"
        })

        # Fetch page with search filter
        txs = repo.get_cash_flow_transactions_page(0, 10, search="TEST-CF")
        self.assertGreaterEqual(len(txs), 3)

        # Check order: newest (2026-03-01) should be at index 0, oldest at the bottom
        check_nos = [t["check_no"] for t in txs if t["check_no"].startswith("TEST-CF")]
        self.assertEqual(check_nos, ["TEST-CF-003", "TEST-CF-002", "TEST-CF-001"])

    def test_classification_filtering_and_balance(self):
        """Verify filtering by classification (e.g. GCash) returns only that account's transactions and accurate balances."""
        # Insert GCash and Cash on Hand transactions
        repo.add_cash_flow_transaction({
            "date": "2026-01-10",
            "check_no": "TEST-CF-GC1",
            "particulars": "GCash",
            "deposit": 5000.0,
            "withdrawal": 0.0,
        })
        repo.add_cash_flow_transaction({
            "date": "2026-01-11",
            "check_no": "TEST-CF-COH1",
            "particulars": "Cash on Hand",
            "deposit": 3000.0,
            "withdrawal": 0.0,
        })
        repo.add_cash_flow_transaction({
            "date": "2026-01-12",
            "check_no": "TEST-CF-GC2",
            "particulars": "GCash",
            "deposit": 0.0,
            "withdrawal": 1500.0,
        })

        # GCash Summary
        summary = repo.get_cash_flow_summary(search="TEST-CF", classification="GCash")
        self.assertEqual(summary["total_deposits"], 5000.0)
        self.assertEqual(summary["total_withdrawals"], 1500.0)
        self.assertEqual(summary["current_balance"], 3500.0)

        # GCash Transactions page
        gcash_txs = repo.get_cash_flow_transactions_page(0, 10, search="TEST-CF", classification="GCash")
        self.assertEqual(len(gcash_txs), 2)
        # Newest first
        self.assertEqual(gcash_txs[0]["check_no"], "TEST-CF-GC2")
        self.assertEqual(gcash_txs[0]["balance"], 3500.0)
        self.assertEqual(gcash_txs[1]["check_no"], "TEST-CF-GC1")
        self.assertEqual(gcash_txs[1]["balance"], 5000.0)

    def test_transaction_modal_features(self):
        """Verify TransactionModal segmented buttons, presets, and default classification."""
        dlg = TransactionModal(default_classification="GCash")
        self.assertEqual(dlg._tx_type, "deposit")
        self.assertEqual(dlg._part_f.currentText(), "GCash")

        # Test switching to withdrawal
        dlg._set_tx_type("withdrawal")
        self.assertEqual(dlg._tx_type, "withdrawal")

        # Test presets
        dlg._amount_f.setValue(100.0)
        dlg._add_preset(500.0)
        self.assertEqual(dlg._amount_f.value(), 600.0)

        # Test account chip
        dlg._set_account_chip("Maya")
        self.assertEqual(dlg._part_f.currentText(), "Maya")


if __name__ == "__main__":
    unittest.main()
