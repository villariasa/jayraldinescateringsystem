"""
Popup dialog for selecting and customizing dishes for a catering package during booking.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QCheckBox, QWidget
)
from PySide6.QtCore import Qt, QSize
import utils.repository as repo
from utils.theme import ThemeManager


def _is_light():
    try:
        return ThemeManager().current_theme == "light"
    except Exception:
        return False


class PackageMenuSelectionDialog(QDialog):
    """Modal popup dialog to select/customize dishes for a specific package during booking."""

    def __init__(self, pkg: dict, selected_names: list = None, parent=None):
        super().__init__(parent)
        self.pkg = pkg or {}
        self._pkg_id = self.pkg.get("id")
        self._pkg_name = self.pkg.get("name", "Catering Package")
        self._price = float(self.pkg.get("price_per_pax", 0))
        self._initial_selected = [s.strip().lower() for s in (selected_names or []) if s]
        self._dish_checks = []
        self.confirmed_dishes = []

        self.setWindowTitle(f"Select Dishes & Menu — {self._pkg_name}")
        self.resize(680, 620)
        self.setMinimumSize(540, 480)

        bg_color = "#FFFFFF" if _is_light() else "#0B1220"
        text_color = "#0F172A" if _is_light() else "#F8FAFC"
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {text_color};
            }}
        """)

        self._build_ui()

    def _build_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(22, 20, 22, 20)
        root_lay.setSpacing(14)

        # ── Header ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t_lbl = QLabel(f"🍽️ Menu Selection: {self._pkg_name}")
        t_lbl.setStyleSheet("font-size: 17px; font-weight: 800; color: #E11D48;")
        p_sub = QLabel(f"Rate: ₱{self._price:,.2f} / set · Min set: 1 Set (4 dishes good for 22 person)")
        p_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_col.addWidget(t_lbl)
        title_col.addWidget(p_sub)
        header.addLayout(title_col)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
                color: #EF4444;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        root_lay.addLayout(header)

        # ── Quick Action Toolbar ─────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self._count_lbl = QLabel("✓ 0 dishes selected")
        self._count_lbl.setStyleSheet("font-size: 12.5px; font-weight: 700; color: #10B981;")
        bar.addWidget(self._count_lbl)
        bar.addStretch()

        btn_defaults = QPushButton("✓ Package Defaults")
        btn_defaults.setCursor(Qt.PointingHandCursor)
        btn_defaults.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.12);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.22);
            }
        """)
        btn_defaults.clicked.connect(self._reset_to_defaults)
        bar.addWidget(btn_defaults)

        btn_all = QPushButton("Select All")
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.07);
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.14);
            }
        """)
        btn_all.clicked.connect(self._select_all)
        bar.addWidget(btn_all)

        btn_clear = QPushButton("Clear All")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.07);
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
            }
        """)
        btn_clear.clicked.connect(self._clear_all)
        bar.addWidget(btn_clear)

        root_lay.addLayout(bar)

        # ── Scrollable Dishes List ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.05);
                width: 7px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.25);
                min-height: 25px;
                border-radius: 3px;
            }
        """)

        list_container = QWidget()
        list_container.setStyleSheet("background: transparent;")
        list_lay = QVBoxLayout(list_container)
        list_lay.setContentsMargins(16, 12, 16, 16)
        list_lay.setSpacing(6)

        # Load package items and catalog items
        default_items = repo.get_package_items(self._pkg_id) if self._pkg_id else []
        self._default_names = {p["item_name"].strip().lower() for p in default_items if p.get("item_name")}

        # Load this package's selection buckets (dish/dessert quotas).
        self._pkg_buckets = (repo.get_package_buckets(self._pkg_id) if self._pkg_id else []) or []
        self._cat_to_bucket = {}
        self._bucket_limit_by_id = {}
        self._bucket_name_by_id = {}
        for b in self._pkg_buckets:
            self._bucket_limit_by_id[b["id"]] = int(b.get("limit") or 0)
            self._bucket_name_by_id[b["id"]] = b.get("name", "")
            for c in b.get("categories", []):
                self._cat_to_bucket[str(c).strip().lower()] = b["id"]
        buckets_active = len(self._pkg_buckets) > 0

        all_items = repo.get_available_menu_items() or default_items

        # Prechecked selection
        if self._initial_selected:
            prechecked = set(self._initial_selected)
        else:
            prechecked = self._default_names

        # Group by category. With buckets active, only show bucketed categories.
        by_cat = {}
        for itm in all_items:
            cat = itm.get("category") or "Main Course"
            if buckets_active and str(cat).strip().lower() not in self._cat_to_bucket:
                continue
            by_cat.setdefault(cat, []).append(itm)

        # Live per-bucket counter summary.
        if buckets_active:
            self._bucket_summary = QLabel("")
            self._bucket_summary.setWordWrap(True)
            self._bucket_summary.setStyleSheet("font-size: 11px; font-weight: 700; color: #38BDF8; padding: 2px 4px;")
            list_lay.addWidget(self._bucket_summary)
        else:
            self._bucket_summary = None

        cat_order = ["Main Course", "Appetizer", "Soup", "Salad", "Dessert", "Beverage", "Drinks", "Other"]
        sorted_cats = sorted(by_cat.keys(), key=lambda c: cat_order.index(c) if c in cat_order else 99)

        for cat in sorted_cats:
            b_id = self._cat_to_bucket.get(str(cat).strip().lower()) if buckets_active else None
            hdr_txt = f"● {cat.upper()}"
            if b_id is not None:
                hdr_txt += f"  —  {self._bucket_name_by_id.get(b_id, '')} (max {self._bucket_limit_by_id.get(b_id, 0)})"
            cat_hdr = QLabel(hdr_txt)
            cat_hdr.setStyleSheet("font-size: 11px; font-weight: 800; color: #E11D48; margin-top: 10px; margin-bottom: 2px; letter-spacing: 0.5px;")
            list_lay.addWidget(cat_hdr)

            for item in by_cat[cat]:
                i_name = (item.get("item") or item.get("name") or item.get("item_name") or "").strip()
                if not i_name:
                    continue

                row = QHBoxLayout()
                row.setContentsMargins(6, 3, 6, 3)
                row.setSpacing(10)

                chk = QCheckBox(i_name)
                chk.setStyleSheet("""
                    QCheckBox {
                        font-size: 13px;
                        font-weight: 600;
                        color: #E2E8F0;
                        spacing: 8px;
                    }
                    QCheckBox::indicator {
                        width: 17px;
                        height: 17px;
                        border-radius: 4px;
                        border: 1.5px solid #475569;
                        background: rgba(255, 255, 255, 0.05);
                    }
                    QCheckBox::indicator:checked {
                        background: #E11D48;
                        border-color: #E11D48;
                    }
                """)
                if i_name.lower() in prechecked:
                    chk.setChecked(True)

                if buckets_active:
                    chk.toggled.connect(self._make_toggle_handler(chk, item))
                else:
                    chk.toggled.connect(self._on_toggled)

                is_default = i_name.lower() in self._default_names
                badge = QLabel("Package Default" if is_default else "")
                badge.setStyleSheet("font-size: 10px; font-weight: 700; color: #10B981; background: rgba(16, 185, 129, 0.12); border-radius: 4px; padding: 1px 7px;")
                if not is_default:
                    badge.hide()

                row.addWidget(chk)
                row.addWidget(badge)
                row.addStretch()

                self._dish_checks.append((chk, item))
                list_lay.addLayout(row)

        list_lay.addStretch()
        scroll.setWidget(list_container)
        root_lay.addWidget(scroll, 1)

        # ── Bottom Action Buttons ───────────────────────────────────────────
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.07);
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.14);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        bottom_bar.addWidget(cancel_btn)

        bottom_bar.addStretch()

        apply_btn = QPushButton("  Confirm & Apply Dishes")
        apply_btn.setFixedHeight(38)
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.setStyleSheet("""
            QPushButton {
                background: #E11D48;
                color: #FFFFFF;
                border: 1px solid #BE123C;
                border-radius: 6px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background: #BE123C;
            }
        """)
        apply_btn.clicked.connect(self._apply_and_close)
        bottom_bar.addWidget(apply_btn)

        root_lay.addLayout(bottom_bar)

        self._on_toggled()

    def _on_toggled(self):
        cnt = sum(1 for chk, _ in self._dish_checks if chk.isChecked())
        self._count_lbl.setText(f"✓ {cnt} dish{'es' if cnt != 1 else ''} selected")
        self._update_bucket_counters()

    # ---- Selection bucket enforcement (dish/dessert quotas) ----
    def _bucket_for_item(self, item):
        cat = (item.get("category") or "").strip().lower()
        return getattr(self, "_cat_to_bucket", {}).get(cat)

    def _count_checked_in_bucket(self, bid):
        n = 0
        for chk, itm in self._dish_checks:
            if chk.isChecked() and self._bucket_for_item(itm) == bid:
                n += 1
        return n

    def _update_bucket_counters(self):
        lbl = getattr(self, "_bucket_summary", None)
        if not lbl:
            return
        parts = []
        for b in getattr(self, "_pkg_buckets", []) or []:
            used = self._count_checked_in_bucket(b["id"])
            parts.append(f"{b.get('name', '')} {used}/{b.get('limit', 0)}")
        lbl.setText("   •   ".join(parts))
        lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #38BDF8; padding: 2px 4px;")

    def _flash_bucket_limit(self, bid, limit):
        name = getattr(self, "_bucket_name_by_id", {}).get(bid, "This group")
        lbl = getattr(self, "_bucket_summary", None)
        if lbl:
            lbl.setText(f"⚠️ {name}: max {limit} — remove one to pick another.")
            lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #F59E0B; padding: 2px 4px;")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1800, self._update_bucket_counters)

    def _make_toggle_handler(self, chk, item):
        def _handler(checked=False):
            if checked:
                bid = self._bucket_for_item(item)
                if bid is not None:
                    limit = getattr(self, "_bucket_limit_by_id", {}).get(bid, 0)
                    if self._count_checked_in_bucket(bid) > limit:
                        chk.blockSignals(True)
                        chk.setChecked(False)
                        chk.blockSignals(False)
                        self._flash_bucket_limit(bid, limit)
                        return
            self._on_toggled()
        return _handler

    def _reset_to_defaults(self):
        for chk, itm in self._dish_checks:
            name = (itm.get("item") or itm.get("name") or itm.get("item_name") or "").strip().lower()
            chk.blockSignals(True)
            chk.setChecked(name in self._default_names)
            chk.blockSignals(False)
        self._on_toggled()

    def _select_all(self):
        # Respect bucket caps: never select more than each bucket's limit.
        if getattr(self, "_pkg_buckets", None):
            counts = {}
            for chk, itm in self._dish_checks:
                bid = self._bucket_for_item(itm)
                chk.blockSignals(True)
                if bid is None:
                    chk.setChecked(False)
                else:
                    limit = getattr(self, "_bucket_limit_by_id", {}).get(bid, 0)
                    used = counts.get(bid, 0)
                    if used < limit:
                        chk.setChecked(True)
                        counts[bid] = used + 1
                    else:
                        chk.setChecked(False)
                chk.blockSignals(False)
            self._on_toggled()
            return
        for chk, _ in self._dish_checks:
            chk.setChecked(True)
        self._on_toggled()

    def _clear_all(self):
        for chk, _ in self._dish_checks:
            chk.blockSignals(True)
            chk.setChecked(False)
            chk.blockSignals(False)
        self._on_toggled()

    def _apply_and_close(self):
        self.confirmed_dishes = [
            (itm.get("item") or itm.get("name") or itm.get("item_name") or "").strip()
            for chk, itm in self._dish_checks
            if chk.isChecked() and (itm.get("item") or itm.get("name") or itm.get("item_name"))
        ]
        self.accept()

    def get_selected_dishes(self) -> list[str]:
        return self.confirmed_dishes
