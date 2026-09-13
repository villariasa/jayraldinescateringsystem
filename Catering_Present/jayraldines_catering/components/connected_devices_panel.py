"""
Connected Terminals & Database Server Monitoring Panel.
Displays real-time database connection metrics and active client workstations.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from utils.accent import AccentManager
from utils.db import get_server_connection_stats, get_connected_devices


class ConnectedDevicesPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("connectedDevicesPanel")
        self.setStyleSheet("""
            QFrame#connectedDevicesPanel {
                background-color: transparent;
                border: none;
            }
        """)

        self._build_ui()

        # 10-second auto refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(10_000)
        self._refresh_timer.timeout.connect(self.refresh_data)
        self._refresh_timer.start()

        # Initial load
        QTimer.singleShot(50, self.refresh_data)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        # ── Header ─────────────────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)

        title_lbl = QLabel("🖥️ Connected Terminals & Server Activity")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        sub_lbl = QLabel("Live database connection telemetry and active network workstations")
        sub_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")

        v_titles.addWidget(title_lbl)
        v_titles.addWidget(sub_lbl)
        hdr_row.addLayout(v_titles, 1)

        self._auto_refresh_chk = QCheckBox("Live Sync (10s)")
        self._auto_refresh_chk.setChecked(True)
        self._auto_refresh_chk.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self._auto_refresh_chk.toggled.connect(self._on_auto_refresh_toggled)
        hdr_row.addWidget(self._auto_refresh_chk)

        self._refresh_btn = QPushButton("  Refresh")
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.setFixedHeight(32)
        self._refresh_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """)
        self._refresh_btn.clicked.connect(self.refresh_data)
        hdr_row.addWidget(self._refresh_btn)

        lay.addLayout(hdr_row)

        # ── KPI Stats Bar ───────────────────────────────────────────────────
        self._kpi_row = QHBoxLayout()
        self._kpi_row.setSpacing(12)

        self._card_db = self._create_kpi_card("Database Server", "PostgreSQL", "⚡ Connected")
        self._card_devices = self._create_kpi_card("Active Terminals", "0 Online", "🖥️ Network")
        self._card_conns = self._create_kpi_card("DB Connections", "1 Active", "🔌 Pool: 5–32")
        self._card_ping = self._create_kpi_card("Server Latency", "0.0 ms", "📶 Ping")

        self._kpi_row.addWidget(self._card_db)
        self._kpi_row.addWidget(self._card_devices)
        self._kpi_row.addWidget(self._card_conns)
        self._kpi_row.addWidget(self._card_ping)
        lay.addLayout(self._kpi_row)

        # ── Table of Devices ────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Terminal / Machine", "IP Address", "Active User",
            "Current Screen", "App Version", "Status", "Last Seen"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setMinimumHeight(200)
        self.table.setMaximumHeight(320)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        lay.addWidget(self.table)

    def _create_kpi_card(self, title: str, value: str, sub: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet("""
            QFrame {
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 10px 14px;
            }
        """)
        v = QVBoxLayout(f)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; color: #94A3B8; font-weight: 600; text-transform: uppercase;")
        lbl_v = QLabel(value)
        lbl_v.setObjectName("kpiVal")
        lbl_v.setStyleSheet("font-size: 15px; color: #F8FAFC; font-weight: 800;")
        lbl_s = QLabel(sub)
        lbl_s.setObjectName("kpiSub")
        lbl_s.setStyleSheet("font-size: 11px; color: #64748B;")

        v.addWidget(lbl_t)
        v.addWidget(lbl_v)
        v.addWidget(lbl_s)
        return f

    def _on_auto_refresh_toggled(self, checked: bool):
        if checked:
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()

    def refresh_data(self):
        """Fetch live stats and refresh device monitoring table."""
        try:
            stats = get_server_connection_stats()
            devices = get_connected_devices()

            # Update KPI Cards
            self._card_db.findChild(QLabel, "kpiVal").setText(stats.get("database_name", "PostgreSQL"))
            self._card_db.findChild(QLabel, "kpiSub").setText(f"Engine: {stats.get('engine', 'postgres').upper()}")

            online_cnt = stats.get("active_devices_count", 0)
            total_cnt = stats.get("total_registered_devices", 0)
            self._card_devices.findChild(QLabel, "kpiVal").setText(f"{online_cnt} Online")
            self._card_devices.findChild(QLabel, "kpiSub").setText(f"{total_cnt} Total Terminals")

            if stats.get("engine") == "sqlite":
                self._card_conns.findChild(QLabel, "kpiVal").setText("Embedded")
                self._card_conns.findChild(QLabel, "kpiSub").setText("Direct File Access (WAL)")
            else:
                pg_conns = stats.get("pg_active_connections", 1)
                p_min = stats.get("pool_min", 5)
                p_max = stats.get("pool_max", 32)
                self._card_conns.findChild(QLabel, "kpiVal").setText(f"{pg_conns} Active")
                self._card_conns.findChild(QLabel, "kpiSub").setText(f"Pool Capacity: {p_min}–{p_max}")

            ping_ms = stats.get("ping_ms", 0.0)
            self._card_ping.findChild(QLabel, "kpiVal").setText(f"{ping_ms} ms")
            self._card_ping.findChild(QLabel, "kpiSub").setText("Excellent Latency" if ping_ms < 15 else "Normal Latency")

            # Populate Table
            self.table.setRowCount(len(devices))
            for row_idx, dev in enumerate(devices):
                # Terminal Name & ID
                host = dev.get("hostname", "Unknown")
                dev_id = dev.get("device_id", "")
                os_info = dev.get("os_info", "")
                name_item = QTableWidgetItem(f"{host}  ({dev_id})")
                name_item.setToolTip(f"OS: {os_info}\nDevice ID: {dev_id}")

                # IP Address
                ip_item = QTableWidgetItem(dev.get("ip_address", "127.0.0.1"))
                ip_item.setTextAlignment(Qt.AlignCenter)

                # Active User & Role
                user = dev.get("username") or "—"
                role = dev.get("user_role") or "—"
                user_item = QTableWidgetItem(f"{user} ({role})" if user != "—" else "—")
                user_item.setTextAlignment(Qt.AlignCenter)

                # Current Screen
                screen = dev.get("active_module", "Dashboard")
                screen_item = QTableWidgetItem(screen)
                screen_item.setTextAlignment(Qt.AlignCenter)

                # App Version
                ver = dev.get("app_version", "v4.1.15")
                ver_item = QTableWidgetItem(ver)
                ver_item.setTextAlignment(Qt.AlignCenter)

                # Status Badge
                live_st = dev.get("live_status", "offline")
                if live_st == "online":
                    st_text = "🟢 Online"
                elif live_st == "idle":
                    st_text = "🟡 Idle"
                else:
                    st_text = "⚪ Offline"
                st_item = QTableWidgetItem(st_text)
                st_item.setTextAlignment(Qt.AlignCenter)

                # Last Seen Relative
                sec = dev.get("seconds_since_ping", 0) or 0
                if sec < 45:
                    last_seen_txt = "Just now"
                elif sec < 120:
                    last_seen_txt = f"{sec}s ago"
                elif sec < 3600:
                    last_seen_txt = f"{sec // 60}m ago"
                elif sec < 86400:
                    last_seen_txt = f"{sec // 3600}h ago"
                else:
                    last_seen_txt = f"{sec // 86400}d ago"

                seen_item = QTableWidgetItem(last_seen_txt)
                seen_item.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(row_idx, 0, name_item)
                self.table.setItem(row_idx, 1, ip_item)
                self.table.setItem(row_idx, 2, user_item)
                self.table.setItem(row_idx, 3, screen_item)
                self.table.setItem(row_idx, 4, ver_item)
                self.table.setItem(row_idx, 5, st_item)
                self.table.setItem(row_idx, 6, seen_item)

        except Exception as e:
            print(f"[ConnectedDevicesPanel] Refresh error: {e}")
