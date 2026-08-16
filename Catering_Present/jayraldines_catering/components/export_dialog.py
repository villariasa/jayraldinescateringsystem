"""
ExportWizardDialog — Data Export Wizard for Jayraldine's Catering System.
Allows exporting All System Data (Master Excel Workbook) or specific entities
(Bookings, Customers, Expenses, Menu Items, Billing Invoices) in Excel (.xlsx) or CSV format.
"""
import os
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QComboBox, QRadioButton, QButtonGroup, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from utils.theme import ThemeManager
from utils.accent import AccentManager
from utils.icons import btn_icon_primary, btn_icon_secondary, get_icon
from utils.animations import animate_dialog_open, create_soft_shadow
import utils.exporter as exporter


class ExportWizardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export System Data — Jayraldine's Catering System")
        self.setMinimumWidth(540)
        self.setModal(True)
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("modalCard")
        create_soft_shadow(container, radius=32, y_offset=8, opacity=45)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(24, 24, 24, 20)
        inner.setSpacing(16)

        # Header Row
        head_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("export").pixmap(QSize(28, 28)))
        head_row.addWidget(icon_lbl)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        title = QLabel("Export Data Wizard")
        title.setObjectName("h2")
        sub = QLabel("Export system records to Excel (.xlsx) or CSV files.")
        sub.setObjectName("subtitle")
        v_head.addWidget(title)
        v_head.addWidget(sub)
        head_row.addLayout(v_head, 1)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#98A2B3", size=QSize(14, 14)))
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        head_row.addWidget(close_btn, alignment=Qt.AlignTop)
        inner.addLayout(head_row)

        div = QFrame()
        div.setObjectName("divider")
        inner.addWidget(div)

        # Entity Selector Group
        lbl_entity = QLabel("Select Data to Export:")
        lbl_entity.setStyleSheet("font-weight: 700; font-size: 13px;")
        inner.addWidget(lbl_entity)

        self.combo_entity = QComboBox()
        self.combo_entity.addItems([
            "All System Data (Master Excel Workbook)",
            "Bookings & Orders Directory",
            "Customers Directory",
            "Expenses & Operating Costs",
            "Menu Items & Packages",
            "Billing & Payment Invoices"
        ])
        self.combo_entity.setFixedHeight(36)
        inner.addWidget(self.combo_entity)

        # File Format Selector Group
        lbl_format = QLabel("Select File Format:")
        lbl_format.setStyleSheet("font-weight: 700; font-size: 13px; padding-top: 6px;")
        inner.addWidget(lbl_format)

        fmt_box = QFrame()
        fmt_box.setObjectName("cardElevated")
        f_lay = QHBoxLayout(fmt_box)
        f_lay.setContentsMargins(14, 10, 14, 10)
        f_lay.setSpacing(20)

        self.rb_excel = QRadioButton("Excel Spreadsheet (.xlsx) — Recommended")
        self.rb_csv   = QRadioButton("CSV Document (.csv)")
        self.rb_excel.setChecked(True)

        self.bg_format = QButtonGroup(self)
        self.bg_format.addButton(self.rb_excel)
        self.bg_format.addButton(self.rb_csv)

        f_lay.addWidget(self.rb_excel)
        f_lay.addWidget(self.rb_csv)
        f_lay.addStretch()
        inner.addWidget(fmt_box)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_export = QPushButton(" Export File...")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.setIcon(btn_icon_primary("export"))
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._do_export)
        btn_row.addWidget(self.btn_export)

        inner.addLayout(btn_row)
        outer.addWidget(container)

    def _do_export(self):
        sel_entity = self.combo_entity.currentText()
        is_excel = self.rb_excel.isChecked()
        ext = ".xlsx" if is_excel else ".csv"
        filter_str = "Excel Files (*.xlsx)" if is_excel else "CSV Files (*.csv)"

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        if "Bookings" in sel_entity:
            default_name = f"jayraldines_bookings_{now_str}{ext}"
        elif "Customers" in sel_entity:
            default_name = f"jayraldines_customers_{now_str}{ext}"
        elif "Expenses" in sel_entity:
            default_name = f"jayraldines_expenses_{now_str}{ext}"
        elif "Menu" in sel_entity:
            default_name = f"jayraldines_menu_{now_str}{ext}"
        elif "Billing" in sel_entity:
            default_name = f"jayraldines_billings_{now_str}{ext}"
        else:
            default_name = f"jayraldines_master_export_{now_str}{ext}"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Export File", default_name, filter_str
        )
        if not file_path:
            return

        try:
            success_ok = exporter.export_custom_entity_data(sel_entity, is_excel, file_path)
            if success_ok:
                ans = QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Data successfully exported to:\n{file_path}\n\nWould you like to open the file location?",
                    QMessageBox.Open | QMessageBox.Ok,
                    QMessageBox.Open
                )
                if ans == QMessageBox.Open:
                    try:
                        folder = os.path.dirname(file_path)
                        if os.name == "nt":
                            os.startfile(folder)
                        else:
                            subprocess.Popen(["xdg-open", folder])
                    except Exception:
                        pass
                self.accept()
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to export data. Please check openpyxl installation.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred during export:\n{e}")
