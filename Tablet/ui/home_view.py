from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QFileDialog, QMessageBox, QInputDialog, QDialog
)
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtCore import Qt, Signal

import utils.repository as repo
import utils.importer as importer
import utils.exporter as exporter
from utils.session import get_actor, set_actor
from ui import theme
from ui.terms_modal import TermsModal


class ClickableCard(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: #132238;
                border: 1px solid #1E293B;
                border-radius: 12px;
            }
            QFrame:hover {
                background-color: #182B46;
                border: 1px solid #334155;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class RecentOrdersModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recent Tablet Orders")
        self.setFixedSize(650, 480)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 16px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Recent Tablet Orders")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                color: #94A3B8;
                font-size: 14px;
                font-weight: bold;
                border-radius: 16px;
                border: none;
            }
            QPushButton:hover {
                background: #334155;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        lay.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(8)

        orders = repo.get_all_orders()
        if not orders:
            empty_lbl = QLabel("No orders recorded on this tablet yet.")
            empty_lbl.setStyleSheet("color: #94A3B8; font-size: 14px; padding: 40px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            c_lay.addWidget(empty_lbl)
        else:
            for o in orders:
                card = QFrame()
                card.setStyleSheet("""
                    QFrame {
                        background-color: #132238;
                        border: 1px solid #1E293B;
                        border-radius: 10px;
                    }
                """)
                cl = QHBoxLayout(card)
                cl.setContentsMargins(16, 12, 16, 12)

                info = QVBoxLayout()
                info.setSpacing(2)
                ref_lbl = QLabel(f"{o['booking_ref']}  —  {o['customer']}")
                ref_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
                sub_lbl = QLabel(f"Event: {o['event_date']} · Created: {o.get('created_at', '')}")
                sub_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
                info.addWidget(ref_lbl)
                info.addWidget(sub_lbl)
                cl.addLayout(info, 3)

                status_color = theme.STATUS_COLORS.get(o["status"], theme.TEXT_MUTED)
                pill = QLabel(o["status"])
                pill.setStyleSheet(theme.pill_style(status_color))
                pill.setAlignment(Qt.AlignCenter)
                cl.addWidget(pill)

                amt_lbl = QLabel(f"₱{o['total']:,.2f}")
                amt_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #F59E0B;")
                amt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                cl.addWidget(amt_lbl, 1)

                c_lay.addWidget(card)

        c_lay.addStretch()
        scroll.setWidget(container)
        lay.addWidget(scroll)


class DataSyncModal(QDialog):
    def __init__(self, parent=None, on_reload=None):
        super().__init__(parent)
        self._on_reload = on_reload
        self.setWindowTitle("Data Sync & Operations")
        self.setFixedSize(580, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 16px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Data Synchronization & Backup")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                color: #94A3B8;
                font-size: 14px;
                font-weight: bold;
                border-radius: 16px;
                border: none;
            }
            QPushButton:hover {
                background: #334155;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        lay.addLayout(header)

        self._status_lbl = QLabel()
        self._status_lbl.setStyleSheet("font-size: 13px; color: #94A3B8;")
        self._status_lbl.setWordWrap(True)
        lay.addWidget(self._status_lbl)
        self._update_status()

        # Action Buttons
        btn_grid = QVBoxLayout()
        btn_grid.setSpacing(10)

        import_btn = QPushButton("📥  Import Master Data (Packages & Menu)")
        import_btn.setFixedHeight(44)
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                color: #F8FAFC;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid #334155;
                text-align: left;
                padding-left: 16px;
            }
            QPushButton:hover { background: #334155; }
        """)
        import_btn.clicked.connect(self._import_master_data)
        btn_grid.addWidget(import_btn)

        template_btn = QPushButton("📄  Download Excel Menu Template")
        template_btn.setFixedHeight(44)
        template_btn.setCursor(Qt.PointingHandCursor)
        template_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                color: #F8FAFC;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid #334155;
                text-align: left;
                padding-left: 16px;
            }
            QPushButton:hover { background: #334155; }
        """)
        template_btn.clicked.connect(self._download_template)
        btn_grid.addWidget(template_btn)

        export_btn = QPushButton("📤  Export Orders for PC Import (.db)")
        export_btn.setFixedHeight(44)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                color: #F8FAFC;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid #334155;
                text-align: left;
                padding-left: 16px;
            }
            QPushButton:hover { background: #334155; }
        """)
        export_btn.clicked.connect(self._export_orders)
        btn_grid.addWidget(export_btn)

        archive_btn = QPushButton("📦  Archive & Clear Orders (Excel)")
        archive_btn.setFixedHeight(44)
        archive_btn.setCursor(Qt.PointingHandCursor)
        archive_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #F87171;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid #EF4444;
                text-align: left;
                padding-left: 16px;
            }
            QPushButton:hover { background: rgba(239, 68, 68, 0.25); }
        """)
        archive_btn.clicked.connect(self._archive_and_clear_orders)
        btn_grid.addWidget(archive_btn)

        lay.addLayout(btn_grid)
        lay.addStretch()

    def _update_status(self):
        last_sync = importer.get_last_master_sync()
        if last_sync:
            self._status_lbl.setText(
                f"Current Database Status:\n"
                f"• Last Synced: {last_sync['tms_imported_at']}\n"
                f"• Packages Available: {last_sync['tms_packages_count']}\n"
                f"• Menu Dishes: {last_sync['tms_menu_items_count']}"
            )
        else:
            self._status_lbl.setText("No master data imported yet. Use the option below to import your menu from the PC app.")

    def _import_master_data(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Master Data File", "",
            "Master Data Files (*.db *.xlsx *.xlsm);;SQLite Database (*.db);;Excel Files (*.xlsx *.xlsm);;All Files (*)",
        )
        if not path:
            return
        stats = importer.import_master_data(path)
        if stats.get("errors"):
            QMessageBox.warning(self, "Import Failed", "\n".join(stats["errors"]))
            return
        QMessageBox.information(
            self, "Import Complete",
            f"{stats['packages']} Packages\n{stats['menu_items']} Menu Items\n{stats['package_items']} Package Items\n\n"
            "The tablet will now use this updated menu/package structure for new orders.",
        )
        self._update_status()
        if self._on_reload:
            self._on_reload()

    def _download_template(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel Template", "tablet_master_data_template.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        ok = importer.generate_sample_excel_template(path)
        if ok:
            QMessageBox.information(
                self, "Template Saved",
                f"Template saved to:\n{path}\n\nFill in your Packages and Menu Items sheets, then use 'Import Master Data' to load it.",
            )
        else:
            QMessageBox.warning(self, "Failed", "Could not generate the template.")

    def _export_orders(self):
        from datetime import datetime as _dt
        default_name = f"tablet_orders_{_dt.now().strftime('%Y%m%d_%H%M%S')}.db"
        path, _ = QFileDialog.getSaveFileName(self, "Export Orders for PC Import", default_name, "SQLite Database (*.db)")
        if not path:
            return
        ok = importer.export_local_database(path)
        if ok:
            QMessageBox.information(
                self, "Export Complete",
                f"Orders exported to:\n{path}\n\nOn the PC, use Settings → 'Merge Backup File Into This Database' to import these orders.",
            )
        else:
            QMessageBox.warning(self, "Export Failed", "Could not export the orders file.")

    def _archive_and_clear_orders(self):
        from datetime import datetime as _dt
        orders = repo.get_all_orders()
        if not orders:
            QMessageBox.information(self, "No Orders", "There are currently no orders on this tablet to archive or clear.")
            return

        confirm_msg = (
            f"Are you sure you want to clear all {len(orders)} orders on this tablet?\n\n"
            "SAFETY BACKUP:\n"
            "Before clearing, the system will export and save all orders to an Excel (.xlsx) file "
            "with full customer details, menu selections, and payment history stamped with the current date & time."
        )
        reply = QMessageBox.question(
            self, "Archive & Clear Orders", confirm_msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        default_name = f"Jayraldines_Tablet_Orders_{_dt.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Orders Archive (Excel)", default_name, "Excel Files (*.xlsx);;All Files (*)"
        )
        if not path:
            return

        res = exporter.export_all_orders_to_excel(path)
        if not res["success"]:
            QMessageBox.critical(
                self, "Archive Failed",
                f"Could not save Excel archive:\n{res.get('error', 'Unknown error')}\n\n"
                "Orders were NOT cleared for safety."
            )
            return

        cleared_count = repo.clear_all_orders()
        self._update_status()
        if self._on_reload:
            self._on_reload()

        QMessageBox.information(
            self, "Orders Archived & Cleared",
            f"Successfully saved {res['orders_count']} orders to Excel:\n{path}\n\n"
            f"Cleared {cleared_count} local orders from the tablet. Ready for new customers!"
        )


class HomeView(QWidget):
    def __init__(self, on_new_order, on_toggle_fullscreen=None):
        super().__init__()
        self._on_new_order = on_new_order
        self._on_toggle_fullscreen = on_toggle_fullscreen
        self._build_ui()
        self.reload()

    def _start_order_flow(self):
        modal = TermsModal(self)
        if modal.exec() == QDialog.Accepted:
            self._on_new_order()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignCenter)

        # Outer centered container frame matching the screenshot
        self._outer_card = QFrame()
        self._outer_card.setObjectName("HomeOuterCard")
        self._outer_card.setStyleSheet("""
            QFrame#HomeOuterCard {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 20px;
            }
        """)
        self._outer_card.setMaximumWidth(980)

        self._card_lay = QVBoxLayout(self._outer_card)
        self._card_lay.setContentsMargins(36, 32, 36, 32)
        self._card_lay.setSpacing(24)

        # ── 1. TOP HEADER ──
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(14)
        header.setAlignment(Qt.AlignVCenter)

        # Left brand group: Avatar + Titles
        brand_group = QHBoxLayout()
        brand_group.setSpacing(14)
        brand_group.setAlignment(Qt.AlignVCenter)

        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(48, 48)
        avatar_lbl.setAlignment(Qt.AlignCenter)
        logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                avatar_lbl.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if avatar_lbl.pixmap().isNull() if avatar_lbl.pixmap() else True:
            avatar_lbl.setText("JC")
            avatar_lbl.setStyleSheet("""
                background-color: #C2410C;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 900;
                border-radius: 24px;
            """)
        brand_group.addWidget(avatar_lbl, alignment=Qt.AlignVCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setAlignment(Qt.AlignVCenter)

        brand_title = QLabel("Jayraldine's Catering")
        brand_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        brand_sub = QLabel("Self Service Tablet Kiosk")
        brand_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(brand_title)
        title_box.addWidget(brand_sub)
        brand_group.addLayout(title_box)

        header.addLayout(brand_group)
        header.addStretch()

        # Right tools: Fullscreen + Shield (Owner Settings)
        right_tools = QHBoxLayout()
        right_tools.setSpacing(10)
        right_tools.setAlignment(Qt.AlignVCenter)

        if self._on_toggle_fullscreen:
            fs_btn = QPushButton()
            fs_btn.setIcon(theme.create_fullscreen_icon("#94A3B8", 18))
            fs_btn.setToolTip("Toggle Fullscreen (F11)")
            fs_btn.setFixedSize(44, 44)
            fs_btn.setCursor(Qt.PointingHandCursor)
            fs_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: #334155;
                }
            """)
            fs_btn.clicked.connect(self._on_toggle_fullscreen)
            right_tools.addWidget(fs_btn)

        shield_btn = QPushButton()
        shield_btn.setIcon(theme.create_shield_icon("#94A3B8", 22))
        shield_btn.setToolTip("Owner Settings & Setup")
        shield_btn.setFixedSize(44, 44)
        shield_btn.setCursor(Qt.PointingHandCursor)
        shield_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        shield_btn.clicked.connect(self._open_owner_settings)
        right_tools.addWidget(shield_btn)

        header.addLayout(right_tools)
        self._card_lay.addLayout(header)

        # ── 2. HERO ORDER CARD (EXACT MATCH) ──
        hero_frame = QFrame()
        hero_frame.setStyleSheet("""
            QFrame {
                background-color: #132238;
                border: 1px solid #1E293B;
                border-radius: 16px;
            }
        """)
        hero_lay = QVBoxLayout(hero_frame)
        hero_lay.setContentsMargins(32, 28, 32, 28)
        hero_lay.setSpacing(8)

        eyebrow = QLabel("PLAN YOUR EVENT BUFFET")
        eyebrow.setStyleSheet("font-size: 11px; font-weight: 800; letter-spacing: 2px; color: #94A3B8;")
        hero_lay.addWidget(eyebrow)

        h1 = QLabel("Build your catering order")
        h1.setStyleSheet("font-size: 26px; font-weight: 800; color: #FFFFFF; padding-bottom: 8px;")
        hero_lay.addWidget(h1)

        body_row = QHBoxLayout()
        body_row.setSpacing(20)
        body_row.setAlignment(Qt.AlignVCenter)

        # Left squircle logo badge
        logo_box = QLabel()
        logo_box.setFixedSize(68, 68)
        logo_box.setAlignment(Qt.AlignCenter)
        logo_box.setStyleSheet("""
            background-color: #1E293B;
            border: 1.5px solid #334155;
            border-radius: 16px;
        """)
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                logo_box.setPixmap(pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        body_row.addWidget(logo_box, alignment=Qt.AlignVCenter)

        # Right: Description + CTA button
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        desc = QLabel(
            "Pick a buffet package, choose your dishes, add custom add-ons, "
            "and get an instant cost breakdown with a booking reference."
        )
        desc.setStyleSheet("font-size: 13px; color: #94A3B8; line-height: 1.4;")
        desc.setWordWrap(True)
        right_col.addWidget(desc)

        cta_row = QHBoxLayout()
        cta_btn = QPushButton("Start Your Order  >")
        cta_btn.setFixedSize(190, 46)
        cta_btn.setCursor(Qt.PointingHandCursor)
        cta_btn.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B;
                color: #0F172A;
                font-size: 15px;
                font-weight: 800;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #FBBF24;
            }
            QPushButton:pressed {
                background-color: #D97706;
            }
        """)
        cta_btn.clicked.connect(self._start_order_flow)
        cta_row.addWidget(cta_btn)
        cta_row.addStretch()

        right_col.addLayout(cta_row)
        body_row.addLayout(right_col, 1)

        hero_lay.addLayout(body_row)
        self._card_lay.addWidget(hero_frame)

        # ── 3. BOTTOM CARDS (RECENT ORDERS & SYNCED) ──
        self._bottom_row = QHBoxLayout()
        self._bottom_row.setSpacing(16)

        # Card 1: Recent Orders
        self._recent_card = ClickableCard()
        r_lay = QHBoxLayout(self._recent_card)
        r_lay.setContentsMargins(18, 16, 18, 16)
        r_lay.setSpacing(14)
        r_lay.setAlignment(Qt.AlignVCenter)

        r_icon_box = QLabel()
        r_icon_box.setFixedSize(40, 40)
        r_icon_box.setAlignment(Qt.AlignCenter)
        r_icon_box.setStyleSheet("background-color: #1E293B; border-radius: 8px;")
        r_icon_box.setPixmap(theme.create_clock_icon("#94A3B8", 20).pixmap(20, 20))
        r_lay.addWidget(r_icon_box)

        r_text_box = QVBoxLayout()
        r_text_box.setSpacing(2)
        r_title = QLabel("Recent Orders")
        r_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        self._recent_sub = QLabel("0 orders this week")
        self._recent_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        r_text_box.addWidget(r_title)
        r_text_box.addWidget(self._recent_sub)
        r_lay.addLayout(r_text_box)
        r_lay.addStretch()

        r_chev = QLabel()
        r_chev.setPixmap(theme.create_chevron_right_icon("#64748B", 18).pixmap(18, 18))
        r_lay.addWidget(r_chev)
        self._recent_card.clicked.connect(self._open_recent_orders_modal)
        self._bottom_row.addWidget(self._recent_card, 1)

        # Card 2: Synced
        self._sync_card = ClickableCard()
        s_lay = QHBoxLayout(self._sync_card)
        s_lay.setContentsMargins(18, 16, 18, 16)
        s_lay.setSpacing(14)
        s_lay.setAlignment(Qt.AlignVCenter)

        s_icon_box = QLabel()
        s_icon_box.setFixedSize(40, 40)
        s_icon_box.setAlignment(Qt.AlignCenter)
        s_icon_box.setStyleSheet("background-color: #1E293B; border-radius: 8px;")
        s_icon_box.setPixmap(theme.create_sync_icon("#10B981", 20).pixmap(20, 20))
        s_lay.addWidget(s_icon_box)

        s_text_box = QVBoxLayout()
        s_text_box.setSpacing(2)
        s_title = QLabel("Synced")
        s_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        self._sync_sub = QLabel("Tap to manage master data & backup")
        self._sync_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        s_text_box.addWidget(s_title)
        s_text_box.addWidget(self._sync_sub)
        s_lay.addLayout(s_text_box)
        s_lay.addStretch()

        s_chev = QLabel()
        s_chev.setPixmap(theme.create_chevron_right_icon("#64748B", 18).pixmap(18, 18))
        s_lay.addWidget(s_chev)
        self._sync_card.clicked.connect(self._open_sync_modal)
        self._bottom_row.addWidget(self._sync_card, 1)

        self._card_lay.addLayout(self._bottom_row)
        root.addWidget(self._outer_card, alignment=Qt.AlignCenter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        is_portrait = w < 768
        if hasattr(self, "_outer_card") and hasattr(self, "_bottom_row"):
            if is_portrait:
                self._outer_card.setMaximumWidth(16777215)
                self._card_lay.setContentsMargins(16, 20, 16, 20)
                self._bottom_row.setDirection(QHBoxLayout.TopToBottom)
            else:
                self._outer_card.setMaximumWidth(980)
                self._card_lay.setContentsMargins(36, 32, 36, 32)
                self._bottom_row.setDirection(QHBoxLayout.LeftToRight)

    def reload(self):
        # Update sync label in card
        last_sync = importer.get_last_master_sync()
        if last_sync:
            imported_at = last_sync.get("tms_imported_at", "")
            # Try formatting cleanly
            try:
                dt = datetime.fromisoformat(imported_at)
                time_str = dt.strftime("%b %d, %H:%M")
            except Exception:
                time_str = imported_at[:16] if imported_at else "Recently"
            pkgs = last_sync.get("tms_packages_count", 0)
            items = last_sync.get("tms_menu_items_count", 0)
            self._sync_sub.setText(f"{time_str} · {pkgs} packages, {items} items")
        else:
            self._sync_sub.setText("No master data synced yet · Tap to import")

        # Update recent orders count
        orders = repo.get_all_orders()
        total_count = len(orders)
        if total_count == 0:
            self._recent_sub.setText("0 orders recorded")
        elif total_count == 1:
            self._recent_sub.setText("1 order recorded")
        else:
            self._recent_sub.setText(f"{total_count} orders recorded")

    def _open_recent_orders_modal(self):
        dlg = RecentOrdersModal(self)
        dlg.exec()

    def _open_sync_modal(self):
        dlg = DataSyncModal(self, on_reload=self.reload)
        dlg.exec()

    def _open_owner_settings(self):
        from ui.owner_settings_modal import OwnerSettingsModal
        dlg = OwnerSettingsModal(self)
        dlg.exec()
        self.reload()
