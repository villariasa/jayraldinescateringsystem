from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QFileDialog, QMessageBox, QInputDialog, QDialog
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

import utils.repository as repo
import utils.importer as importer
import utils.exporter as exporter
from utils.session import get_actor, set_actor
from ui import theme
from ui.terms_modal import TermsModal


def _card(elevated=False):
    f = QFrame()
    theme.style_card(f, elevated=elevated)
    return f


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
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(20)

        # ── TOP HEADER (PERFECTLY ALIGNED) ──
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(14)
        header.setAlignment(Qt.AlignVCenter)

        # Brand / Logo Box
        brand_box = QHBoxLayout()
        brand_box.setSpacing(14)
        brand_box.setAlignment(Qt.AlignVCenter)

        logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
        if logo_path.exists():
            logo_lbl = QLabel()
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                logo_lbl.setPixmap(pix.scaled(54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logo_lbl.setFixedSize(54, 54)
                logo_lbl.setAlignment(Qt.AlignCenter)
                brand_box.addWidget(logo_lbl, alignment=Qt.AlignVCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setAlignment(Qt.AlignVCenter)
        title = QLabel("Jayraldine's Catering")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Self-Service Tablet Kiosk")
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        brand_box.addLayout(title_box)
        header.addLayout(brand_box)
        header.addStretch()

        # Top Right Actions (Fixed Heights, Clean Alignment)
        right_actions = QHBoxLayout()
        right_actions.setSpacing(10)
        right_actions.setAlignment(Qt.AlignVCenter)

        if self._on_toggle_fullscreen:
            fs_btn = QPushButton()
            fs_btn.setIcon(theme.create_fullscreen_icon("#CBD5E1", 20))
            fs_btn.setToolTip("Toggle Fullscreen (F11)")
            fs_btn.setObjectName("Secondary")
            fs_btn.setFixedSize(40, 40)
            fs_btn.setCursor(Qt.PointingHandCursor)
            fs_btn.clicked.connect(self._on_toggle_fullscreen)
            right_actions.addWidget(fs_btn, alignment=Qt.AlignVCenter)

        actor_card = QFrame()
        theme.style_card(actor_card, elevated=True)
        actor_card.setFixedHeight(40)
        actor_lay = QHBoxLayout(actor_card)
        actor_lay.setContentsMargins(14, 0, 14, 0)
        actor_lay.setSpacing(8)
        actor_lay.setAlignment(Qt.AlignVCenter)
        self._actor_lbl = QLabel()
        self._actor_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #E2E8F0;")
        actor_lay.addWidget(self._actor_lbl, alignment=Qt.AlignVCenter)
        actor_btn = QPushButton("Staff")
        actor_btn.setObjectName("Ghost")
        actor_btn.setFixedHeight(28)
        actor_btn.setCursor(Qt.PointingHandCursor)
        actor_btn.clicked.connect(self._set_actor)
        actor_lay.addWidget(actor_btn, alignment=Qt.AlignVCenter)

        right_actions.addWidget(actor_card, alignment=Qt.AlignVCenter)
        header.addLayout(right_actions)
        root.addLayout(header)

        # ── KIOSK HERO / ATTRACT BANNER ──
        hero_card = _card(elevated=True)
        hero_lay = QVBoxLayout(hero_card)
        hero_lay.setContentsMargins(28, 24, 28, 24)
        hero_lay.setSpacing(14)

        hero_title = QLabel("CATERING SELF-SERVICE ORDERING")
        hero_title.setStyleSheet("font-size: 14px; font-weight: 900; letter-spacing: 1.5px; color: #D97706;")
        hero_lay.addWidget(hero_title)

        hero_h1 = QLabel("Plan & Customize Your Event Buffet")
        hero_h1.setStyleSheet("font-size: 26px; font-weight: 800; color: #FFFFFF;")
        hero_lay.addWidget(hero_h1)

        hero_desc = QLabel(
            "Select your preferred buffet package, pick your dishes, choose custom add-ons, "
            "and receive an instant cost breakdown with booking reference."
        )
        hero_desc.setStyleSheet(theme.subtitle_style(14))
        hero_desc.setWordWrap(True)
        hero_lay.addWidget(hero_desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        new_order_btn = QPushButton("START YOUR CATERING ORDER ->")
        new_order_btn.setObjectName("Primary")
        new_order_btn.setMinimumHeight(56)
        new_order_btn.setCursor(Qt.PointingHandCursor)
        new_order_btn.setStyleSheet("""
            QPushButton#Primary {
                font-size: 16px;
                font-weight: 800;
                padding: 12px 28px;
                background-color: #D97706;
                color: #FFFFFF;
                border-radius: 8px;
            }
            QPushButton#Primary:hover {
                background-color: #B45309;
            }
        """)
        new_order_btn.clicked.connect(self._start_order_flow)
        btn_row.addWidget(new_order_btn, 2)
        btn_row.addStretch(1)
        hero_lay.addLayout(btn_row)
        root.addWidget(hero_card)

        # ── DATA SYNC & OPERATIONS CARD ──
        sync_card = _card()
        sync_lay = QVBoxLayout(sync_card)
        sync_lay.setContentsMargins(20, 16, 20, 16)
        sync_lay.setSpacing(10)

        sync_title = QLabel("Data Sync & Tools")
        sync_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #D97706;")
        sync_lay.addWidget(sync_title)

        self._sync_lbl = QLabel()
        self._sync_lbl.setStyleSheet(theme.subtitle_style(12))
        sync_lay.addWidget(self._sync_lbl)

        sync_btn_row = QHBoxLayout()
        sync_btn_row.setSpacing(10)

        import_btn = QPushButton("Import Master Data")
        import_btn.setObjectName("Secondary")
        import_btn.setMinimumHeight(44)
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._import_master_data)
        sync_btn_row.addWidget(import_btn)

        template_btn = QPushButton("Excel Template")
        template_btn.setObjectName("Ghost")
        template_btn.setMinimumHeight(44)
        template_btn.setCursor(Qt.PointingHandCursor)
        template_btn.clicked.connect(self._download_template)
        sync_btn_row.addWidget(template_btn)

        export_btn = QPushButton("Export Orders to PC")
        export_btn.setObjectName("Secondary")
        export_btn.setMinimumHeight(44)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_orders)
        sync_btn_row.addWidget(export_btn)

        settings_btn = QPushButton("Owner Settings")
        settings_btn.setObjectName("Secondary")
        settings_btn.setMinimumHeight(44)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self._open_owner_settings)
        sync_btn_row.addWidget(settings_btn)

        clear_btn = QPushButton("Archive & Clear Orders (Excel)")
        clear_btn.setObjectName("Danger")
        clear_btn.setMinimumHeight(44)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._archive_and_clear_orders)
        sync_btn_row.addWidget(clear_btn)

        sync_btn_row.addStretch()
        sync_lay.addLayout(sync_btn_row)
        root.addWidget(sync_card)

        # ── RECENT ORDERS SECTION (PRIVACY / KIOSK TOGGLE) ──
        orders_header = QHBoxLayout()
        orders_header.setContentsMargins(0, 8, 0, 4)
        
        list_title = QLabel("Recent Orders")
        list_title.setStyleSheet("font-size: 17px; font-weight: 800;")
        orders_header.addWidget(list_title)
        orders_header.addStretch()

        self._show_recent_orders = False  # Hidden by default for Customer Data Privacy
        self._toggle_orders_btn = QPushButton("Show Recent Orders")
        self._toggle_orders_btn.setObjectName("Secondary")
        self._toggle_orders_btn.setMinimumHeight(36)
        self._toggle_orders_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_orders_btn.clicked.connect(self._toggle_orders_visibility)
        orders_header.addWidget(self._toggle_orders_btn)

        root.addLayout(orders_header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setVisible(self._show_recent_orders)
        root.addWidget(self._scroll, 1)

    def _toggle_orders_visibility(self):
        self._show_recent_orders = not self._show_recent_orders
        self._scroll.setVisible(self._show_recent_orders)
        if self._show_recent_orders:
            self._toggle_orders_btn.setText("Hide Orders (Privacy Mode)")
            self._toggle_orders_btn.setObjectName("Primary")
        else:
            self._toggle_orders_btn.setText("Show Recent Orders")
            self._toggle_orders_btn.setObjectName("Secondary")
        self._toggle_orders_btn.style().unpolish(self._toggle_orders_btn)
        self._toggle_orders_btn.style().polish(self._toggle_orders_btn)

    def reload(self):
        self._actor_lbl.setText(f"Staff: {get_actor()}")

        last_sync = importer.get_last_master_sync()
        if last_sync:
            self._sync_lbl.setText(
                f"Last synced {last_sync['tms_imported_at']} — "
                f"{last_sync['tms_packages_count']} packages, {last_sync['tms_menu_items_count']} menu items"
            )
        else:
            self._sync_lbl.setText("No master data imported yet. Import a file from the PC before creating orders.")

        orders = repo.get_all_orders()
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setSpacing(10)

        if not orders:
            empty = _card()
            el = QVBoxLayout(empty)
            el.setContentsMargins(20, 24, 20, 24)
            lbl = QLabel("No orders yet. Tap 'Start New Order' to get started.")
            lbl.setStyleSheet(theme.subtitle_style(14))
            lbl.setAlignment(Qt.AlignCenter)
            el.addWidget(lbl)
            lay.addWidget(empty)
        else:
            for o in orders:
                card = _card(elevated=True)
                cl = QHBoxLayout(card)
                cl.setContentsMargins(18, 14, 18, 14)

                info = QVBoxLayout()
                info.setSpacing(3)
                ref_lbl = QLabel(f"{o['booking_ref']}  —  {o['customer']}")
                ref_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
                sub_lbl = QLabel(f"Event: {o['event_date']}")
                sub_lbl.setStyleSheet(theme.subtitle_style(12))
                info.addWidget(ref_lbl)
                info.addWidget(sub_lbl)
                cl.addLayout(info, 3)

                status_color = theme.STATUS_COLORS.get(o["status"], theme.TEXT_MUTED)
                pill = QLabel(o["status"])
                pill.setStyleSheet(theme.pill_style(status_color))
                pill.setAlignment(Qt.AlignCenter)
                cl.addWidget(pill)

                amt_lbl = QLabel(f"₱{o['total']:,.2f}")
                amt_lbl.setStyleSheet("font-size: 15px; font-weight: 800;")
                amt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                cl.addWidget(amt_lbl, 1)

                lay.addWidget(card)

        lay.addStretch()
        self._scroll.setWidget(container)

    def _set_actor(self):
        name, ok = QInputDialog.getText(self, "Staff Name", "Enter your name:")
        if ok and name.strip():
            set_actor(name.strip())
            self._actor_lbl.setText(f"Staff: {get_actor()}")

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
        self.reload()

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
            QMessageBox.warning(self, "Failed", "Could not generate the template. Make sure openpyxl is installed.")

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

    def _open_owner_settings(self):
        from ui.owner_settings_modal import OwnerSettingsModal
        dlg = OwnerSettingsModal(self)
        dlg.exec()
        self.reload()

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

        # Safely clear tablet orders after successful Excel archive
        cleared_count = repo.clear_all_orders()
        self.reload()

        QMessageBox.information(
            self, "Orders Archived & Cleared",
            f"Successfully saved {res['orders_count']} orders to Excel:\n{path}\n\n"
            f"Cleared {cleared_count} local orders from the tablet. Ready for new customers!"
        )

