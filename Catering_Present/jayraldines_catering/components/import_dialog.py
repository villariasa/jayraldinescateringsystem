"""
ImportWizardDialog — Interactive Data Import Wizard for Jayraldine's Catering System.
Features:
- 1-Click Fast Import: Select file & immediately import without tedious manual mapping.
- Intelligent Auto-Detection: Auto-detects Bookings, Customers, Expenses, and Menu Items.
- Full 4-Step Stepper for users who want to preview or customize column mapping.
"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QFileDialog, QMessageBox, QProgressBar, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.accent import AccentManager
from utils.icons import btn_icon_primary, btn_icon_secondary, get_icon
import utils.importer as importer


class ImportWizardDialog(QDialog):
    def __init__(self, default_entity: str = "all_in_one", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Data — Jayraldine's Catering System")
        self.setMinimumSize(880, 640)
        self.setObjectName("card")

        self._entity_type = default_entity
        self._file_path = ""
        self._headers = []
        self._data_rows = []
        self._mapping = {}
        self._prepared_rows = []
        self._counts = {}
        self._master_dict = {}

        self._setup_ui()
        self._load_entity(default_entity)

    def _setup_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(24, 24, 24, 24)
        root_lay.setSpacing(18)

        # ── HEADER ──────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("export").pixmap(QSize(28, 28)))
        header_row.addWidget(icon_lbl)

        v_title = QVBoxLayout()
        v_title.setSpacing(2)
        self._title_lbl = QLabel("Data Import Wizard")
        self._title_lbl.setObjectName("h2")
        self._sub_lbl = QLabel("Import Bookings, Customers, Expenses, or Menu Items from CSV / Excel")
        self._sub_lbl.setObjectName("subtitle")
        v_title.addWidget(self._title_lbl)
        v_title.addWidget(self._sub_lbl)
        header_row.addLayout(v_title, 1)

        # Entity Selector
        self._entity_combo = QComboBox()
        for k, v in importer.ENTITY_SCHEMAS.items():
            self._entity_combo.addItem(v["title"], k)
        self._entity_combo.setMinimumWidth(220)
        self._entity_combo.currentIndexChanged.connect(self._on_entity_changed)
        header_row.addWidget(self._entity_combo)

        # Download Template Button
        self._btn_template = QPushButton(" Download Template")
        self._btn_template.setObjectName("secondaryButton")
        self._btn_template.setIcon(btn_icon_secondary("export"))
        self._btn_template.clicked.connect(self._on_download_template)
        header_row.addWidget(self._btn_template)

        root_lay.addLayout(header_row)

        # ── WIZARD STEP INDICATOR ───────────────────────────────────────────
        step_row = QHBoxLayout()
        step_row.setSpacing(8)
        self._step_labels = []
        steps_text = ["1. Select File", "2. Map Columns", "3. Preview & Validate", "4. Import"]
        for idx, t in enumerate(steps_text):
            lbl = QLabel(t)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedHeight(30)
            lbl.setStyleSheet(
                "border-radius: 15px; font-weight: 700; font-size: 12px; padding: 0 14px; "
                "background: #1E293B; color: #94A3B8;"
            )
            step_row.addWidget(lbl)
            self._step_labels.append(lbl)
        root_lay.addLayout(step_row)

        # ── STACKED WIZARD PAGES ─────────────────────────────────────────────
        self.stack = QStackedWidget()
        root_lay.addWidget(self.stack, 1)

        self._build_step1_file_select()
        self._build_step2_column_mapping()
        self._build_step3_validation_preview()
        self._build_step4_import_execution()

        # ── FOOTER NAVIGATION BUTTONS ───────────────────────────────────────
        footer = QHBoxLayout()
        footer.setSpacing(12)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setObjectName("secondaryButton")
        self._btn_cancel.clicked.connect(self.reject)
        footer.addWidget(self._btn_cancel)

        footer.addStretch()

        self._btn_back = QPushButton("Back")
        self._btn_back.setObjectName("secondaryButton")
        self._btn_back.clicked.connect(self._on_back)
        footer.addWidget(self._btn_back)

        self._btn_next = QPushButton("Next: Map Columns")
        self._btn_next.setObjectName("primaryButton")
        self._btn_next.clicked.connect(self._on_next)
        footer.addWidget(self._btn_next)

        root_lay.addLayout(footer)
        self._update_step_ui(0)

    # ── STEP BUILDERS ────────────────────────────────────────────────────────

    def _build_step1_file_select(self):
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(16)

        desc = QLabel(
            "Select your CSV or Excel (.xlsx) spreadsheet. "
            "Our intelligent engine will auto-detect all columns and categories automatically."
        )
        desc.setObjectName("subtitle")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        self._txt_file = QLineEdit()
        self._txt_file.setPlaceholderText("Select file path (e.g. all_in_one_import_template.xlsx)…")
        file_row.addWidget(self._txt_file, 1)

        btn_browse = QPushButton(" Browse File…")
        btn_browse.setObjectName("primaryButton")
        btn_browse.setIcon(btn_icon_primary("search"))
        btn_browse.clicked.connect(self._on_browse_file)
        file_row.addWidget(btn_browse)
        lay.addLayout(file_row)

        # File Details Box
        self._file_info_card = QFrame()
        self._file_info_card.setObjectName("cardElevated")
        info_lay = QVBoxLayout(self._file_info_card)
        info_lay.setContentsMargins(18, 16, 18, 16)
        info_lay.setSpacing(10)

        self._lbl_file_stats = QLabel("No file selected yet. Click 'Browse File…' to choose your spreadsheet.")
        self._lbl_file_stats.setObjectName("subtitle")
        info_lay.addWidget(self._lbl_file_stats)

        # Fast 1-Click Import Action Row
        self._fast_import_row = QHBoxLayout()
        self._btn_fast_import = QPushButton(" ⚡ Import All Data Now (1-Click)")
        self._btn_fast_import.setObjectName("primaryButton")
        self._btn_fast_import.setFixedHeight(40)
        self._btn_fast_import.setStyleSheet("font-size: 14px; font-weight: 800; padding: 0 20px;")
        self._btn_fast_import.setVisible(False)
        self._btn_fast_import.clicked.connect(self._on_fast_import)
        self._fast_import_row.addWidget(self._btn_fast_import)
        self._fast_import_row.addStretch()
        info_lay.addLayout(self._fast_import_row)

        lay.addWidget(self._file_info_card)
        lay.addStretch()
        self.stack.addWidget(page)

    def _build_step2_column_mapping(self):
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        lbl = QLabel("All columns have been auto-mapped. You can review or adjust any field below:")
        lbl.setObjectName("subtitle")
        lay.addWidget(lbl)

        self._map_table = QTableWidget()
        self._map_table.setColumnCount(3)
        self._map_table.setHorizontalHeaderLabels(["System Field", "Required?", "Matched File Column"])
        self._map_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._map_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._map_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        lay.addWidget(self._map_table, 1)

        self.stack.addWidget(page)

    def _build_step3_validation_preview(self):
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        # Summary Chips
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._lbl_total_cnt = QLabel("Total: 0")
        self._lbl_total_cnt.setStyleSheet("font-weight:700; background:#334155; color:#F8FAFC; border-radius:12px; padding:4px 12px;")
        self._lbl_valid_cnt = QLabel("Valid: 0")
        self._lbl_valid_cnt.setStyleSheet("font-weight:700; background:#166534; color:#DCFCE7; border-radius:12px; padding:4px 12px;")
        self._lbl_warn_cnt = QLabel("Warnings: 0")
        self._lbl_warn_cnt.setStyleSheet("font-weight:700; background:#854D0E; color:#FEF08A; border-radius:12px; padding:4px 12px;")
        self._lbl_err_cnt = QLabel("Errors: 0")
        self._lbl_err_cnt.setStyleSheet("font-weight:700; background:#991B1B; color:#FEE2E2; border-radius:12px; padding:4px 12px;")

        stats_row.addWidget(self._lbl_total_cnt)
        stats_row.addWidget(self._lbl_valid_cnt)
        stats_row.addWidget(self._lbl_warn_cnt)
        stats_row.addWidget(self._lbl_err_cnt)
        stats_row.addStretch()
        lay.addLayout(stats_row)

        self._preview_table = QTableWidget()
        self._preview_table.setAlternatingRowColors(True)
        lay.addWidget(self._preview_table, 1)

        self.stack.addWidget(page)

    def _build_step4_import_execution(self):
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        self._lbl_exec_status = QLabel("Ready to import database records.")
        self._lbl_exec_status.setObjectName("h3")
        lay.addWidget(self._lbl_exec_status)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(22)
        lay.addWidget(self._progress_bar)

        self._lbl_result_summary = QLabel("")
        self._lbl_result_summary.setObjectName("subtitle")
        self._lbl_result_summary.setWordWrap(True)
        lay.addWidget(self._lbl_result_summary)

        lay.addStretch()
        self.stack.addWidget(page)

    # ── LOGIC & HANDLERS ────────────────────────────────────────────────────

    def _load_entity(self, entity_key: str):
        self._entity_type = entity_key
        schema = importer.ENTITY_SCHEMAS.get(entity_key, {})
        idx = self._entity_combo.findData(entity_key)
        if idx >= 0:
            self._entity_combo.setCurrentIndex(idx)
        self._title_lbl.setText(f"Import {schema.get('title', 'Data')}")

    def _on_entity_changed(self, idx: int):
        entity_key = self._entity_combo.itemData(idx)
        self._entity_type = entity_key
        schema = importer.ENTITY_SCHEMAS.get(entity_key, {})
        self._title_lbl.setText(f"Import {schema.get('title', 'Data')}")
        if self._file_path:
            self._parse_selected_file()

    def _on_download_template(self):
        entity_title = importer.ENTITY_SCHEMAS.get(self._entity_type, {}).get("title", "data")
        default_name = f"{self._entity_type}_import_template.xlsx" if self._entity_type == "all_in_one" else f"{self._entity_type}_import_template.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save Sample {entity_title} Template",
            default_name,
            "Excel Spreadsheet (*.xlsx);;CSV Spreadsheet (*.csv)"
        )
        if file_path:
            err = importer.generate_sample_csv(self._entity_type, file_path)
            if err:
                QMessageBox.warning(self, "Download Error", err)
            else:
                QMessageBox.information(
                    self, "Template Downloaded",
                    f"Sample template for {entity_title} downloaded successfully!\n\nLocation:\n{file_path}"
                )

    def _on_browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File to Import",
            "",
            "Spreadsheets (*.csv *.xlsx *.xls);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        if file_path:
            self._txt_file.setText(file_path)
            self._file_path = file_path
            self._parse_selected_file()

    def _parse_selected_file(self):
        if not self._file_path:
            self._btn_fast_import.setVisible(False)
            return

        if self._entity_type == "all_in_one":
            master_dict, err = importer.parse_master_file(self._file_path)
            if err:
                self._lbl_file_stats.setText(f"⚠ Error reading master file: {err}")
                self._headers = []
                self._data_rows = []
                self._master_dict = {}
                self._btn_fast_import.setVisible(False)
                return

            self._master_dict = master_dict
            total_records = sum(len(rows) for _, (_, rows) in master_dict.items())
            breakdown = ", ".join([f"{len(rows)} {k.title()}" for k, (_, rows) in master_dict.items()])
            filename = os.path.basename(self._file_path)
            self._lbl_file_stats.setText(
                f"✅ Master File Loaded: <b>{filename}</b>\n\n"
                f"🎯 <b>Detected Records</b> ({total_records} total): {breakdown}\n\n"
                f"You can click <b>'⚡ Import All Data Now'</b> below to import immediately, or click Next to preview."
            )
            self._btn_fast_import.setVisible(total_records > 0)

            hdrs, rows, _ = importer.parse_file(self._file_path)
            self._headers = hdrs or (next(iter(master_dict.values()))[0] if master_dict else [])
            self._data_rows = rows or (next(iter(master_dict.values()))[1] if master_dict else [])
            self._mapping = importer.auto_map_headers(self._headers, "all_in_one")
            return

        headers, rows, err = importer.parse_file(self._file_path)
        if err:
            self._lbl_file_stats.setText(f"⚠ Error reading file: {err}")
            self._headers = []
            self._data_rows = []
            self._btn_fast_import.setVisible(False)
            return

        self._headers = headers
        self._data_rows = rows
        filename = os.path.basename(self._file_path)
        self._lbl_file_stats.setText(
            f"✅ File Loaded: <b>{filename}</b>\n\n"
            f"• Detected Columns: {len(headers)} columns\n"
            f"• Data Rows: {len(rows)} records\n\n"
            f"Ready to import into Jayraldine's Catering System."
        )
        self._mapping = importer.auto_map_headers(self._headers, self._entity_type)
        self._btn_fast_import.setVisible(len(rows) > 0)

    def _populate_step2_mapping_table(self):
        schema = importer.ENTITY_SCHEMAS.get(self._entity_type, {})
        fields = schema.get("fields", {})

        self._map_table.setRowCount(0)
        self._map_table.setRowCount(len(fields))

        for idx, (field_key, info) in enumerate(fields.items()):
            item_field = QTableWidgetItem(info["label"])
            item_field.setFlags(Qt.ItemIsEnabled)
            self._map_table.setItem(idx, 0, item_field)

            req_str = "YES (Required)" if info.get("required") else "Optional"
            item_req = QTableWidgetItem(req_str)
            item_req.setFlags(Qt.ItemIsEnabled)
            if info.get("required"):
                item_req.setForeground(QColor("#EF4444"))
            self._map_table.setItem(idx, 1, item_req)

            combo = QComboBox()
            combo.addItem("-- Not Mapped --", "")
            matched_header = self._mapping.get(field_key, "")
            selected_index = 0

            for h_idx, h in enumerate(self._headers, start=1):
                combo.addItem(h, h)
                if h == matched_header:
                    selected_index = h_idx

            # If not exact match, check fuzzy alias
            if selected_index == 0 and matched_header:
                for h_idx, h in enumerate(self._headers, start=1):
                    if importer._clean_header_str(h) == importer._clean_header_str(matched_header):
                        selected_index = h_idx
                        break

            combo.setCurrentIndex(selected_index)
            combo.setProperty("field_key", field_key)
            self._map_table.setCellWidget(idx, 2, combo)

    def _read_current_mapping(self):
        mapping = {}
        for row in range(self._map_table.rowCount()):
            combo = self._map_table.cellWidget(row, 2)
            if combo:
                field_key = combo.property("field_key")
                mapping[field_key] = combo.currentData()
        self._mapping = mapping

    def _populate_step3_preview_table(self):
        self._read_current_mapping()
        self._prepared_rows, self._counts = importer.validate_and_prepare_rows(
            self._data_rows, self._mapping, self._entity_type
        )

        schema = importer.ENTITY_SCHEMAS.get(self._entity_type, {})
        field_keys = list(schema.get("fields", {}).keys())
        field_labels = [schema["fields"][k]["label"] for k in field_keys]

        col_headers = ["Row", "Status", "Validation Notes"] + field_labels
        self._preview_table.setRowCount(0)
        self._preview_table.setColumnCount(len(col_headers))
        self._preview_table.setHorizontalHeaderLabels(col_headers)

        total_cnt = len(self._prepared_rows)
        self._lbl_total_cnt.setText(f"Total: {total_cnt}")
        self._lbl_valid_cnt.setText(f"Valid: {self._counts.get('valid', 0)}")
        self._lbl_warn_cnt.setText(f"Warnings: {self._counts.get('warning', 0)}")
        self._lbl_err_cnt.setText(f"Errors: {self._counts.get('error', 0)}")

        self._preview_table.setRowCount(len(self._prepared_rows))
        for row_idx, row_info in enumerate(self._prepared_rows):
            status = row_info["_status"]
            data = row_info["_data"]
            issues_str = "; ".join(row_info["_issues"]) if row_info["_issues"] else "OK"

            it_idx = QTableWidgetItem(str(row_info["_row_index"]))
            it_idx.setFlags(Qt.ItemIsEnabled)

            st_str = "VALID" if status == "valid" else ("WARNING" if status == "warning" else "ERROR")
            it_st = QTableWidgetItem(st_str)
            it_st.setFlags(Qt.ItemIsEnabled)

            if status == "valid":
                it_st.setBackground(QColor("#166534"))
                it_st.setForeground(QColor("#DCFCE7"))
            elif status == "warning":
                it_st.setBackground(QColor("#854D0E"))
                it_st.setForeground(QColor("#FEF08A"))
            else:
                it_st.setBackground(QColor("#991B1B"))
                it_st.setForeground(QColor("#FEE2E2"))

            it_notes = QTableWidgetItem(issues_str)
            it_notes.setFlags(Qt.ItemIsEnabled)

            self._preview_table.setItem(row_idx, 0, it_idx)
            self._preview_table.setItem(row_idx, 1, it_st)
            self._preview_table.setItem(row_idx, 2, it_notes)

            for col_i, k in enumerate(field_keys, start=3):
                val = data.get(k, "")
                if k in ("amount", "total", "price", "total_amount", "expense_amount"):
                    val_str = f"₱ {float(val):,.2f}"
                else:
                    val_str = str(val)
                it_val = QTableWidgetItem(val_str)
                it_val.setFlags(Qt.ItemIsEnabled)
                self._preview_table.setItem(row_idx, col_i, it_val)

        self._preview_table.resizeColumnsToContents()

    def _on_fast_import(self):
        """Direct 1-Click execution from Step 1."""
        self._update_step_ui(3)
        self._execute_import()

    def _execute_import(self):
        if self._entity_type == "all_in_one":
            self._progress_bar.setValue(25)
            total_success = 0
            total_fail = 0
            all_errors = []
            summary_breakdown = []

            master_dict = getattr(self, "_master_dict", None)
            if not master_dict:
                master_dict, _ = importer.parse_master_file(self._file_path)

            if master_dict:
                step_pct = 25
                for ent_key, (hdrs, d_rows) in master_dict.items():
                    if not d_rows:
                        continue
                    mapping = importer.auto_map_headers(hdrs, ent_key)
                    prep_rows, _ = importer.validate_and_prepare_rows(d_rows, mapping, ent_key)
                    s_cnt, f_cnt, errs = importer.execute_batch_import(prep_rows, ent_key, skip_errors=True)
                    total_success += s_cnt
                    total_fail += f_cnt
                    all_errors.extend(errs)
                    summary_breakdown.append(f"• {ent_key.replace('_', ' ').title()}: {s_cnt} imported, {f_cnt} skipped")
                    step_pct += 15
                    self._progress_bar.setValue(min(90, step_pct))

            self._progress_bar.setValue(100)

            if total_success > 0:
                self._lbl_exec_status.setText("✅ All-in-One Master Import Completed!")
                msg = (
                    f"Successfully imported {total_success} total records into Jayraldine's Catering System.\n"
                    f"Skipped / Failed: {total_fail} records.\n\n"
                    f"Section Breakdown:\n" + "\n".join(summary_breakdown) + "\n\n"
                    f"All database tables and application pages have been synchronized."
                )
            else:
                self._lbl_exec_status.setText("⚠ No Records Imported")
                msg = (
                    f"Could not import records from this file. Total skipped: {total_fail}.\n"
                    f"Please verify that the required columns are filled."
                )

            if all_errors:
                msg += "\n\nIssue details:\n" + "\n".join(all_errors[:6])

            self._lbl_result_summary.setText(msg)
            self._btn_next.setText("Finish & Close")
            self._btn_next.setEnabled(True)
            self._emit_refresh_signals()
            return

        valid_cnt = self._counts.get("valid", 0) + self._counts.get("warning", 0)
        if valid_cnt == 0:
            # Re-validate with auto-mapping if coming directly from Fast Import
            self._mapping = importer.auto_map_headers(self._headers, self._entity_type)
            self._prepared_rows, self._counts = importer.validate_and_prepare_rows(
                self._data_rows, self._mapping, self._entity_type
            )
            valid_cnt = self._counts.get("valid", 0) + self._counts.get("warning", 0)

        if valid_cnt == 0:
            QMessageBox.warning(self, "No Valid Rows", "There are no valid data rows to import.")
            return

        self._progress_bar.setValue(50)
        success_cnt, fail_cnt, errors = importer.execute_batch_import(
            self._prepared_rows, self._entity_type, skip_errors=True
        )
        self._progress_bar.setValue(100)

        entity_title = importer.ENTITY_SCHEMAS.get(self._entity_type, {}).get("title", "records")
        if success_cnt > 0:
            self._lbl_exec_status.setText("✅ Import Completed!")
            msg = (
                f"Successfully imported {success_cnt} {entity_title} into the database.\n"
                f"Skipped / Failed: {fail_cnt} records.\n\n"
                f"All active pages have been updated automatically."
            )
        else:
            self._lbl_exec_status.setText("⚠ Import Incomplete")
            msg = f"0 records imported. Skipped / Failed: {fail_cnt} records."

        if errors:
            msg += "\n\nIssue details:\n" + "\n".join(errors[:6])

        self._lbl_result_summary.setText(msg)
        self._btn_next.setText("Finish & Close")
        self._btn_next.setEnabled(True)
        self._emit_refresh_signals()

    def _emit_refresh_signals(self):
        try:
            from utils.signals import app_events
            ev = app_events()
            ev.data_changed.emit()
            ev.booking_saved.emit()
            ev.customer_saved.emit()
            ev.expense_saved.emit()
        except Exception:
            pass

    # ── NAVIGATION STEPS ────────────────────────────────────────────────────

    def _update_step_ui(self, step_idx: int):
        self.stack.setCurrentIndex(step_idx)
        for idx, lbl in enumerate(self._step_labels):
            if idx == step_idx:
                lbl.setStyleSheet(
                    f"border-radius: 15px; font-weight: 700; font-size: 12px; padding: 0 14px; "
                    f"background: {AccentManager().current}; color: #FFFFFF;"
                )
            elif idx < step_idx:
                lbl.setStyleSheet(
                    "border-radius: 15px; font-weight: 700; font-size: 12px; padding: 0 14px; "
                    "background: #10B981; color: #FFFFFF;"
                )
            else:
                lbl.setStyleSheet(
                    "border-radius: 15px; font-weight: 700; font-size: 12px; padding: 0 14px; "
                    "background: #1E293B; color: #94A3B8;"
                )

        self._btn_back.setVisible(step_idx > 0 and step_idx < 3)

        if step_idx == 0:
            self._btn_next.setText("Next: Map Columns")
        elif step_idx == 1:
            self._btn_next.setText("Next: Preview & Validate")
        elif step_idx == 2:
            self._btn_next.setText("Confirm & Import Data")
        elif step_idx == 3:
            self._btn_next.setText("Finish & Close")

    def _on_next(self):
        curr = self.stack.currentIndex()

        if curr == 0:
            if not self._file_path or not self._data_rows:
                QMessageBox.warning(self, "No File Selected", "Please select a valid CSV or Excel file first.")
                return
            self._populate_step2_mapping_table()
            self._update_step_ui(1)
        elif curr == 1:
            self._populate_step3_preview_table()
            self._update_step_ui(2)
        elif curr == 2:
            self._update_step_ui(3)
            self._execute_import()
        elif curr == 3:
            self.accept()

    def _on_back(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self._update_step_ui(curr - 1)
