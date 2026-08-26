from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QFileDialog, QMessageBox, QInputDialog
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

import utils.repository as repo
import utils.importer as importer
from utils.session import get_actor, set_actor
from ui import theme


def _card(elevated=False):
    f = QFrame()
    theme.style_card(f, elevated=elevated)
    return f


class HomeView(QWidget):
    def __init__(self, on_new_order):
        super().__init__()
        self._on_new_order = on_new_order
        self._build_ui()
        self.reload()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(22)

        header = QHBoxLayout()
        header.setSpacing(14)

        logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
        if logo_path.exists():
            logo_lbl = QLabel()
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                logo_lbl.setPixmap(pix.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                header.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Jayraldine's Catering")
        title.setStyleSheet(theme.heading_style(26))
        subtitle = QLabel("Tablet Order Entry")
        subtitle.setStyleSheet(theme.subtitle_style(14))
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        actor_card = QFrame()
        theme.style_card(actor_card, elevated=True)
        actor_lay = QHBoxLayout(actor_card)
        actor_lay.setContentsMargins(14, 8, 14, 8)
        self._actor_lbl = QLabel()
        self._actor_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
        actor_lay.addWidget(self._actor_lbl)
        actor_btn = QPushButton("Change")
        actor_btn.setObjectName("Ghost")
        actor_btn.setCursor(Qt.PointingHandCursor)
        actor_btn.clicked.connect(self._set_actor)
        actor_lay.addWidget(actor_btn)
        header.addWidget(actor_card)
        root.addLayout(header)

        # Primary action
        new_order_btn = QPushButton("＋   Start New Order")
        new_order_btn.setObjectName("Primary")
        new_order_btn.setMinimumHeight(72)
        new_order_btn.setStyleSheet(new_order_btn.styleSheet() + "font-size: 19px;")
        new_order_btn.setCursor(Qt.PointingHandCursor)
        new_order_btn.clicked.connect(self._on_new_order)
        root.addWidget(new_order_btn)

        # Sync card
        sync_card = _card()
        sync_lay = QVBoxLayout(sync_card)
        sync_lay.setContentsMargins(22, 18, 22, 18)
        sync_lay.setSpacing(10)

        sync_title = QLabel("Master Data Sync")
        sync_title.setStyleSheet("font-size: 15px; font-weight: 800;")
        sync_lay.addWidget(sync_title)

        self._sync_lbl = QLabel()
        self._sync_lbl.setStyleSheet(theme.subtitle_style(13))
        self._sync_lbl.setWordWrap(True)
        sync_lay.addWidget(self._sync_lbl)

        sync_btn_row = QHBoxLayout()
        sync_btn_row.setSpacing(10)

        import_btn = QPushButton("⬇  Import Master Data")
        import_btn.setObjectName("Secondary")
        import_btn.setMinimumHeight(52)
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._import_master_data)
        sync_btn_row.addWidget(import_btn)

        template_btn = QPushButton("📄  Download Excel Template")
        template_btn.setObjectName("Ghost")
        template_btn.setMinimumHeight(52)
        template_btn.setCursor(Qt.PointingHandCursor)
        template_btn.clicked.connect(self._download_template)
        sync_btn_row.addWidget(template_btn)

        export_btn = QPushButton("⬆  Export Orders to PC File")
        export_btn.setObjectName("Secondary")
        export_btn.setMinimumHeight(52)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_orders)
        sync_btn_row.addWidget(export_btn)

        sync_btn_row.addStretch()
        sync_lay.addLayout(sync_btn_row)
        root.addWidget(sync_card)

        list_title = QLabel("Recent Orders")
        list_title.setStyleSheet("font-size: 17px; font-weight: 800; margin-top: 4px;")
        root.addWidget(list_title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(self._scroll, 1)

    def reload(self):
        self._actor_lbl.setText(f"👤  {get_actor()}")

        last_sync = importer.get_last_master_sync()
        if last_sync:
            self._sync_lbl.setText(
                f"✔  Last synced {last_sync['tms_imported_at']} — "
                f"{last_sync['tms_packages_count']} packages, {last_sync['tms_menu_items_count']} menu items"
            )
        else:
            self._sync_lbl.setText("⚠  No master data imported yet. Import a file from the PC (or an Excel sheet) before creating orders.")

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
            self._actor_lbl.setText(f"👤  {get_actor()}")

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
