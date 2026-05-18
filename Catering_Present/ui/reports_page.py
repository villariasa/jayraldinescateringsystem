from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QSpacerItem
)
from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtGui import QFont, QColor
from utils import repository


class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        title = QLabel("Reports & Analytics")
        title.setObjectName("pageTitle")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        root.addWidget(title)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        self.cmb_period = QComboBox()
        self.cmb_period.setObjectName("cmbPeriod")
        self.cmb_period.addItems(["This Month", "Last Month", "This Year", "Custom Range"])
        self.cmb_period.currentIndexChanged.connect(self._on_period_changed)
        filter_row.addWidget(QLabel("Period:"))
        filter_row.addWidget(self.cmb_period)

        self.dt_from = QDateEdit()
        self.dt_from.setObjectName("dtFrom")
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(QDate.currentDate().addDays(-30))
        self.dt_from.setVisible(False)
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self.dt_from)

        self.dt_to = QDateEdit()
        self.dt_to.setObjectName("dtTo")
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(QDate.currentDate())
        self.dt_to.setVisible(False)
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self.dt_to)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setObjectName("btnRefresh")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self._load_data)
        filter_row.addWidget(btn_refresh)
        filter_row.addStretch()

        root.addLayout(filter_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.content_lay = QVBoxLayout(content)
        self.content_lay.setSpacing(20)
        self.content_lay.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        root.addWidget(scroll)

        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)

        self.kpi_total_bookings  = self._kpi_card("Total Bookings", "0",      "#3B82F6")
        self.kpi_total_revenue   = self._kpi_card("Total Revenue",  "₱0.00",  "#22C55E")
        self.kpi_unpaid_amount   = self._kpi_card("Unpaid Amount",  "₱0.00",  "#EF4444")
        self.kpi_total_pax       = self._kpi_card("Total Pax",      "0",      "#F59E0B")

        kpi_grid.addWidget(self.kpi_total_bookings, 0, 0)
        kpi_grid.addWidget(self.kpi_total_revenue,  0, 1)
        kpi_grid.addWidget(self.kpi_unpaid_amount,  0, 2)
        kpi_grid.addWidget(self.kpi_total_pax,      0, 3)

        self.content_lay.addLayout(kpi_grid)

        self.content_lay.addWidget(self._section_label("Bookings Summary"))
        self.tbl_bookings = self._make_table(
            ["Booking Ref", "Customer", "Event Date", "Pax", "Total (₱)", "Paid (₱)", "Balance (₱)", "Status"]
        )
        self.content_lay.addWidget(self.tbl_bookings)

        self.content_lay.addWidget(self._section_label("Invoice Summary"))
        self.tbl_invoices = self._make_table(
            ["Invoice Ref", "Booking Ref", "Total (₱)", "Paid (₱)", "Balance (₱)", "Status", "Due Date"]
        )
        self.content_lay.addWidget(self.tbl_invoices)

        self.content_lay.addWidget(self._section_label("Expenses Summary"))
        self.tbl_expenses = self._make_table(
            ["Date", "Category", "Description", "Amount (₱)"]
        )
        self.content_lay.addWidget(self.tbl_expenses)

        self.content_lay.addWidget(self._section_label("Top Menu Items"))
        self.tbl_top_menu = self._make_table(["Menu Item", "Order Count"])
        self.content_lay.addWidget(self.tbl_top_menu)

        self.content_lay.addWidget(self._section_label("Payment Methods"))
        self.tbl_pay_methods = self._make_table(["Method", "Count"])
        self.content_lay.addWidget(self.tbl_pay_methods)

        self.content_lay.addStretch()

    def _kpi_card(self, label: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("kpiCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(6)

        lbl_title = QLabel(label)
        lbl_title.setObjectName("kpiTitle")
        lbl_title.setFont(QFont("Segoe UI", 10))
        lay.addWidget(lbl_title)

        lbl_value = QLabel(value)
        lbl_value.setObjectName("kpiValue")
        lbl_value.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        lbl_value.setStyleSheet(f"color: {color};")
        lay.addWidget(lbl_value)

        card._value_label = lbl_value
        return card

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        return lbl

    def _make_table(self, headers: list) -> QTableWidget:
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        tbl.setMaximumHeight(300)
        return tbl

    def _on_period_changed(self, idx: int):
        is_custom = (idx == 3)
        self.dt_from.setVisible(is_custom)
        self.dt_to.setVisible(is_custom)
        self._load_data()

    def _period_sql_filter(self) -> tuple:
        idx = self.cmb_period.currentIndex()
        today = QDate.currentDate()

        if idx == 0:
            first = QDate(today.year(), today.month(), 1)
            last  = QDate(today.year(), today.month(), today.daysInMonth())
            return "bk_event_date BETWEEN %s AND %s", (
                first.toString("yyyy-MM-dd"),
                last.toString("yyyy-MM-dd"),
            )
        elif idx == 1:
            prev = today.addMonths(-1)
            first = QDate(prev.year(), prev.month(), 1)
            last  = QDate(prev.year(), prev.month(), prev.daysInMonth())
            return "bk_event_date BETWEEN %s AND %s", (
                first.toString("yyyy-MM-dd"),
                last.toString("yyyy-MM-dd"),
            )
        elif idx == 2:
            first = QDate(today.year(), 1, 1)
            last  = QDate(today.year(), 12, 31)
            return "bk_event_date BETWEEN %s AND %s", (
                first.toString("yyyy-MM-dd"),
                last.toString("yyyy-MM-dd"),
            )
        else:
            return "bk_event_date BETWEEN %s AND %s", (
                self.dt_from.date().toString("yyyy-MM-dd"),
                self.dt_to.date().toString("yyyy-MM-dd"),
            )

    def _load_data(self):
        try:
            self._load_kpis()
            self._load_bookings_table()
            self._load_invoices_table()
            self._load_expenses_table()
            self._load_top_menu_table()
            self._load_pay_methods_table()
        except Exception:
            pass

    def _load_kpis(self):
        try:
            kpis = repository.get_report_kpis()
            if kpis:
                self.kpi_total_bookings._value_label.setText(str(kpis.get("total_bookings", 0)))
                self.kpi_total_revenue._value_label.setText(
                    f"₱{float(kpis.get('total_revenue', 0)):,.2f}"
                )
                self.kpi_unpaid_amount._value_label.setText(
                    f"₱{float(kpis.get('unpaid_amount', 0)):,.2f}"
                )
                self.kpi_total_pax._value_label.setText(str(kpis.get("total_pax", 0)))
        except Exception:
            pass

    def _load_bookings_table(self):
        try:
            sql_filter, params = self._period_sql_filter()
            rows = repository.get_bookings_report(sql_filter, params)
            self._fill_table(
                self.tbl_bookings,
                rows,
                ["booking_ref", "customer_name", "event_date", "pax",
                 "total_amount", "amount_paid", "balance", "status"],
            )
        except Exception:
            pass

    def _load_invoices_table(self):
        try:
            rows = repository.get_all_invoices()
            self._fill_table(
                self.tbl_invoices,
                rows,
                ["invoice_ref", "booking_ref", "total_amount", "amount_paid",
                 "balance", "status", "due_date"],
            )
        except Exception:
            pass

    def _load_expenses_table(self):
        try:
            rows = repository.get_all_expenses()
            self._fill_table(
                self.tbl_expenses,
                rows,
                ["expense_date", "category", "description", "amount"],
            )
        except Exception:
            pass

    def _load_top_menu_table(self):
        try:
            rows = repository.get_top_menu_items()
            self._fill_table(self.tbl_top_menu, rows, ["item", "order_count"])
        except Exception:
            pass

    def _load_pay_methods_table(self):
        try:
            rows = repository.get_payment_methods()
            self._fill_table(self.tbl_pay_methods, rows, ["method", "total"])
        except Exception:
            pass

    def _fill_table(self, tbl: QTableWidget, rows: list, keys: list):
        tbl.setRowCount(0)
        if not rows:
            return
        for row_data in rows:
            r = tbl.rowCount()
            tbl.insertRow(r)
            for c, key in enumerate(keys):
                val = row_data.get(key, "")
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                tbl.setItem(r, c, item)

    def filter_search(self, text: str):
        pass
