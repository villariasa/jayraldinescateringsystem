"""
CalendarExportDialog — Dynamic multi-month calendar PDF export wizard.

Lets the user select a date range (start month/year → end month/year),
configure export options, then fires off the PDF export. Defaults to
the current calendar page's displayed month (1 month).
"""
import calendar as _cal
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QFileDialog, QMessageBox, QProgressDialog
)
from PySide6.QtCore import Qt, QSize, QThread, Signal, QObject

from utils.icons import btn_icon_primary, btn_icon_secondary, get_icon
from utils.animations import animate_dialog_open, create_soft_shadow
from components.dialogs import prompt_file_saved


# ─── Background worker so the UI doesn't freeze on large exports ─────────────
class _ExportWorker(QObject):
    finished = Signal(bool)          # success flag
    progress = Signal(int, int, str) # current, total, label

    def __init__(self, save_path, months, biz_name, include_agenda, include_empty):
        super().__init__()
        self.save_path     = save_path
        self.months        = months
        self.biz_name      = biz_name
        self.include_agenda  = include_agenda
        self.include_empty   = include_empty

    def run(self):
        try:
            import utils.repository as repo
            import utils.exporter as _exporter

            # Fetch events for every month in range
            events_by_month = {}
            for i, (y, m) in enumerate(self.months):
                self.progress.emit(i, len(self.months), f"Loading {_cal.month_name[m]} {y}…")
                raw = repo.get_calendar_events_for_month(y, m)
                # Normalise keyed by day (int) within that month
                day_map = {}
                for (ey, em, ed), ev_list in (raw or {}).items():
                    if ey == y and em == m:
                        day_map[ed] = [
                            {
                                **ev,
                                "event_name":    ev.get("name") or ev.get("customer_name", ""),
                                "customer_name": ev.get("customer_name") or ev.get("name", ""),
                                "occasion":      ev.get("occasion") or "",
                                "pax":           ev.get("pax", 0),
                                "time":          ev.get("time", "6:00 PM"),
                                "location":      ev.get("loc") or ev.get("venue", "—"),
                                "venue":         ev.get("venue") or ev.get("loc", "—"),
                                "address":       ev.get("address", ""),
                                "menu":          ev.get("menu") or ev.get("package_name", "—"),
                                "notes":         ev.get("notes") or ev.get("theme") or "",
                                "theme":         ev.get("theme") or ev.get("notes") or "",
                                "description_theme": ev.get("description_theme") or ev.get("notes") or ev.get("theme") or "",
                                "color_theme":   ev.get("color_theme") or ev.get("color") or "#2563EB",
                                "color":         ev.get("color_theme") or ev.get("color") or "#2563EB",
                                "total_amount":  ev.get("total_amount", 0.0),
                                "amount_paid":   ev.get("amount_paid", 0.0),
                                "balance":       ev.get("balance", 0.0),
                                "ref":           ev.get("ref", "—"),
                                "status":        ev.get("status", "CONFIRMED"),
                            }
                            for ev in ev_list
                        ]
                events_by_month[(y, m)] = day_map

            self.progress.emit(len(self.months), len(self.months), "Generating PDF…")
            ok = _exporter.export_calendar_pdf_range(
                save_path      = self.save_path,
                months         = self.months,
                events_by_month= events_by_month,
                biz_name       = self.biz_name,
                include_agenda = self.include_agenda,
                include_empty  = self.include_empty,
            )
            self.finished.emit(ok)
        except Exception as exc:
            import traceback; traceback.print_exc()
            self.finished.emit(False)


class _ExportThread(QThread):
    def __init__(self, worker):
        super().__init__()
        self._worker = worker
        self._worker.moveToThread(self)

    def run(self):
        self._worker.run()


# ─── Main Dialog ──────────────────────────────────────────────────────────────
class CalendarExportDialog(QDialog):
    """
    Multi-month calendar PDF export wizard.

    Usage::
        dlg = CalendarExportDialog(parent=self,
                                   default_year=self.current_year,
                                   default_month=self.current_month,
                                   biz_name=biz_name)
        dlg.exec()
    """

    MONTHS = [_cal.month_name[m] for m in range(1, 13)]
    YEARS  = list(range(datetime.now().year - 3, datetime.now().year + 4))

    def __init__(self, parent=None, default_year=None, default_month=None, biz_name="Jayraldine's Catering"):
        super().__init__(parent)
        self.setWindowTitle("Export Calendar PDF")
        self.setMinimumWidth(520)
        self.setModal(True)

        now = datetime.now()
        self._default_year  = default_year  or now.year
        self._default_month = default_month or now.month
        self._biz_name = biz_name

        self._thread  = None
        self._worker  = None

        self._build_ui()
        self._update_summary()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240)

    # ─── UI builder ──────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("modalCard")
        create_soft_shadow(card, radius=32, y_offset=8, opacity=45)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────
        head_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("calendar", size=QSize(28, 28)).pixmap(QSize(28, 28)))
        head_row.addWidget(icon_lbl)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        title_lbl = QLabel("Export Calendar PDF")
        title_lbl.setObjectName("h2")
        sub_lbl   = QLabel("Select the month range to include in the export.")
        sub_lbl.setObjectName("subtitle")
        v_head.addWidget(title_lbl)
        v_head.addWidget(sub_lbl)
        head_row.addLayout(v_head, 1)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#98A2B3", size=QSize(14, 14)))
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        head_row.addWidget(close_btn, alignment=Qt.AlignTop)
        lay.addLayout(head_row)

        div = QFrame(); div.setObjectName("divider")
        lay.addWidget(div)

        # ── Date Range ────────────────────────────────────────────────────
        lay.addWidget(self._section_label("Date Range"))

        range_box = QFrame()
        range_box.setObjectName("cardElevated")
        rb_lay = QVBoxLayout(range_box)
        rb_lay.setContentsMargins(14, 12, 14, 12)
        rb_lay.setSpacing(10)

        # From row
        from_row = QHBoxLayout()
        from_row.addWidget(QLabel("From:"), 0)
        self.combo_from_month = QComboBox()
        self.combo_from_month.addItems(self.MONTHS)
        self.combo_from_month.setCurrentIndex(self._default_month - 1)
        self.combo_from_month.setFixedHeight(32)
        from_row.addWidget(self.combo_from_month, 2)

        self.spin_from_year = QSpinBox()
        self.spin_from_year.setRange(self.YEARS[0], self.YEARS[-1])
        self.spin_from_year.setValue(self._default_year)
        self.spin_from_year.setFixedHeight(32)
        self.spin_from_year.setFixedWidth(80)
        from_row.addWidget(self.spin_from_year, 1)
        rb_lay.addLayout(from_row)

        # To row
        to_row = QHBoxLayout()
        to_row.addWidget(QLabel("  To:"), 0)
        self.combo_to_month = QComboBox()
        self.combo_to_month.addItems(self.MONTHS)
        self.combo_to_month.setCurrentIndex(self._default_month - 1)
        self.combo_to_month.setFixedHeight(32)
        to_row.addWidget(self.combo_to_month, 2)

        self.spin_to_year = QSpinBox()
        self.spin_to_year.setRange(self.YEARS[0], self.YEARS[-1])
        self.spin_to_year.setValue(self._default_year)
        self.spin_to_year.setFixedHeight(32)
        self.spin_to_year.setFixedWidth(80)
        to_row.addWidget(self.spin_to_year, 1)
        rb_lay.addLayout(to_row)

        lay.addWidget(range_box)

        # ── Summary Badge ─────────────────────────────────────────────────
        self.lbl_summary = QLabel()
        self.lbl_summary.setAlignment(Qt.AlignCenter)
        self.lbl_summary.setStyleSheet(
            "background: rgba(34, 197, 94, 0.12); color: #16A34A; "
            "font-weight: 700; font-size: 12px; padding: 8px 14px; "
            "border-radius: 8px; border: 1px solid rgba(34,197,94,0.25);"
        )
        lay.addWidget(self.lbl_summary)

        # ── Quick presets ─────────────────────────────────────────────────
        lay.addWidget(self._section_label("Quick Presets"))

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        presets = [
            ("This Month",   0),
            ("Next 3 Mo.",   2),
            ("Next 6 Mo.",   5),
            ("Full Year",   11),
            ("Prev 3 Mo.", -3),
        ]
        for lbl, delta in presets:
            btn = QPushButton(lbl)
            btn.setObjectName("secondaryButton")
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, d=delta: self._apply_preset(d))
            preset_row.addWidget(btn)
        lay.addLayout(preset_row)

        # ── Options ───────────────────────────────────────────────────────
        lay.addWidget(self._section_label("Export Options"))

        opt_box = QFrame()
        opt_box.setObjectName("cardElevated")
        opt_lay = QVBoxLayout(opt_box)
        opt_lay.setContentsMargins(14, 10, 14, 10)
        opt_lay.setSpacing(6)

        self.chk_agenda = QCheckBox("Include itemized agenda pages (booking details after each calendar page)")
        self.chk_agenda.setChecked(True)

        self.chk_empty = QCheckBox("Include months with no bookings")
        self.chk_empty.setChecked(False)

        opt_lay.addWidget(self.chk_agenda)
        opt_lay.addWidget(self.chk_empty)
        lay.addWidget(opt_box)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_export = QPushButton("  Export PDF…")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.setIcon(btn_icon_primary("export"))
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._start_export)
        btn_row.addWidget(self.btn_export)

        lay.addLayout(btn_row)
        outer.addWidget(card)

        # Wire up signals
        for w in [self.combo_from_month, self.combo_to_month]:
            w.currentIndexChanged.connect(self._update_summary)
        for w in [self.spin_from_year, self.spin_to_year]:
            w.valueChanged.connect(self._update_summary)

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: 700; font-size: 12px; color: #6B7280; letter-spacing: 0.3px;")
        return lbl

    # ─── Logic ───────────────────────────────────────────────────────────────
    def _get_months_list(self):
        """Return list of (year, month) tuples for the selected range, or [] if invalid."""
        fy = self.spin_from_year.value()
        fm = self.combo_from_month.currentIndex() + 1
        ty = self.spin_to_year.value()
        tm = self.combo_to_month.currentIndex() + 1

        if (fy, fm) > (ty, tm):
            return []

        months = []
        cy, cm = fy, fm
        while (cy, cm) <= (ty, tm):
            months.append((cy, cm))
            cm += 1
            if cm > 12:
                cm = 1; cy += 1
        return months

    def _update_summary(self):
        months = self._get_months_list()
        n = len(months)
        if n == 0:
            self.lbl_summary.setText("⚠  End date must be on or after Start date")
            self.lbl_summary.setStyleSheet(
                "background: rgba(239,68,68,0.1); color: #DC2626; "
                "font-weight: 700; font-size: 12px; padding: 8px 14px; "
                "border-radius: 8px; border: 1px solid rgba(239,68,68,0.25);"
            )
            self.btn_export.setEnabled(False)
            return

        fy, fm = months[0]
        ty, tm = months[-1]
        if n == 1:
            label = f"📅  1 month selected — {_cal.month_name[fm]} {fy}"
        else:
            label = (f"📅  {n} months selected — "
                     f"{_cal.month_name[fm]} {fy} → {_cal.month_name[tm]} {ty}")

        pages_est = n if not self.chk_agenda.isChecked() else n * 2
        label += f"   •   ~{pages_est} PDF page{'s' if pages_est != 1 else ''}"

        self.lbl_summary.setText(label)
        self.lbl_summary.setStyleSheet(
            "background: rgba(34, 197, 94, 0.12); color: #16A34A; "
            "font-weight: 700; font-size: 12px; padding: 8px 14px; "
            "border-radius: 8px; border: 1px solid rgba(34,197,94,0.25);"
        )
        self.btn_export.setEnabled(True)

    def _apply_preset(self, delta):
        """delta > 0 = forward N months; delta < 0 = backward N months."""
        now = datetime.now()
        y, m = now.year, now.month

        if delta >= 0:
            # From this month, to this month + delta
            end_m = m + delta
            end_y = y + (end_m - 1) // 12
            end_m = ((end_m - 1) % 12) + 1
            self.spin_from_year.setValue(y)
            self.combo_from_month.setCurrentIndex(m - 1)
            self.spin_to_year.setValue(end_y)
            self.combo_to_month.setCurrentIndex(end_m - 1)
        else:
            # From this month + delta (backwards), to this month
            start_m = m + delta         # delta is negative
            start_y = y
            while start_m < 1:
                start_m += 12; start_y -= 1
            self.spin_from_year.setValue(start_y)
            self.combo_from_month.setCurrentIndex(start_m - 1)
            self.spin_to_year.setValue(y)
            self.combo_to_month.setCurrentIndex(m - 1)

        self._update_summary()

    # ─── Export flow ─────────────────────────────────────────────────────────
    def _start_export(self):
        months = self._get_months_list()
        if not months:
            return

        fy, fm = months[0]
        ty, tm = months[-1]
        n = len(months)
        default_name = (
            f"jayraldines_calendar_{fy}{fm:02d}.pdf" if n == 1
            else f"jayraldines_calendar_{fy}{fm:02d}_to_{ty}{tm:02d}.pdf"
        )

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Calendar PDF", default_name, "PDF Files (*.pdf)"
        )
        if not save_path:
            return

        # Show progress dialog
        self._progress = QProgressDialog(
            "Loading booking data…", None, 0, len(months), self
        )
        self._progress.setWindowTitle("Exporting Calendar…")
        self._progress.setWindowModality(Qt.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.setValue(0)
        self._progress.show()

        self.btn_export.setEnabled(False)

        # Fire background thread
        self._save_path = save_path
        self._worker = _ExportWorker(
            save_path      = save_path,
            months         = months,
            biz_name       = self._biz_name,
            include_agenda = self.chk_agenda.isChecked(),
            include_empty  = self.chk_empty.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)

        self._thread = _ExportThread(self._worker)
        self._thread.start()

    def _on_progress(self, current, total, label):
        if self._progress:
            self._progress.setLabelText(label)
            self._progress.setValue(current)

    def _on_finished(self, ok):
        if self._progress:
            self._progress.close()
        self.btn_export.setEnabled(True)

        if ok:
            prompt_file_saved(self, self._save_path,
                              title="Calendar PDF Exported",
                              message="Calendar PDF exported successfully.")
            self.accept()
        else:
            QMessageBox.warning(self, "Export Failed",
                                "PDF export failed. Make sure reportlab and pypdf are installed.")
