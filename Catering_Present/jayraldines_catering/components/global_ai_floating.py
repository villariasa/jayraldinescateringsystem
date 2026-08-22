"""
Global Floating AI Assistant Widget & Drawer — allows Chef Jay AI to be accessible
from ANY page in the application.

Features:
- Draggable floating Chef Mascot in bottom-right corner (or anywhere on screen)
- Profile Avatars for both User and Chef Jay AI in chat bubbles
- Floating AI Drawer containing full conversation history, suggested prompt chips,
  and local AI thread runner.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QPoint, QTimer, QMargins, QSize
from PySide6.QtGui import QColor, QPainter, QClipboard, QKeySequence, QShortcut, QPixmap

from utils.theme import ThemeManager
from utils.accent import AccentManager
from utils.icons import get_icon
from utils.paths import resource_path
import utils.ai_client as ai_client
from components.mascot import ChefMascot


def _is_dark():
    return ThemeManager().is_dark()


def _accent_rgba(alpha: float) -> str:
    r, g, b, _ = QColor(AccentManager().current).getRgb()
    return f"rgba({r},{g},{b},{alpha})"


class _AskWorker(QObject):
    finished = Signal(dict)

    def __init__(self, question: str):
        super().__init__()
        self._question = question

    def run(self):
        self.finished.emit(ai_client.ask(self._question))


def build_user_bubble(question: str) -> QWidget:
    """Renders a user message bubble with User Profile Avatar."""
    wrap = QWidget()
    row = QHBoxLayout(wrap)
    row.setContentsMargins(0, 4, 0, 4)
    row.setSpacing(10)
    row.addStretch()

    col = QVBoxLayout()
    col.setSpacing(3)

    header = QLabel("You")
    header.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF;")
    header.setAlignment(Qt.AlignRight)
    col.addWidget(header)

    bubble = QLabel(question)
    bubble.setWordWrap(True)
    bubble.setMaximumWidth(480)
    bubble.setStyleSheet(
        f"background: {AccentManager().current}; color: #FFFFFF; border-radius: 14px; "
        "border-top-right-radius: 2px; padding: 10px 14px; font-size: 13px; "
        "font-weight: 600; line-height: 140%;"
    )
    col.addWidget(bubble)
    row.addLayout(col)

    # User Avatar Badge (SVG Icon Avatar)
    avatar = QLabel()
    avatar.setFixedSize(36, 36)
    avatar.setAlignment(Qt.AlignCenter)
    dark = _is_dark()
    bg = "#1F2937" if dark else "#F1F5F9"
    icon = get_icon("user", color=AccentManager().current, size=QSize(18, 18))
    avatar.setPixmap(icon.pixmap(QSize(18, 18)))
    avatar.setStyleSheet(
        f"background: {bg}; border: 2px solid {AccentManager().current}; border-radius: 18px;"
    )
    row.addWidget(avatar, 0, Qt.AlignTop)
    return wrap


def build_ai_card(answer: str, chart_spec: dict | None = None,
                  error: str = "", action: dict | None = None,
                  options: list | None = None, on_option_send=None,
                  on_action_result=None) -> QWidget:
    """Renders an AI answer card with Chef Jay AI Profile Avatar."""
    card = QFrame()
    card.setObjectName("card")
    main_lay = QVBoxLayout(card)
    main_lay.setContentsMargins(16, 14, 16, 14)
    main_lay.setSpacing(10)

    # Profile Header
    header_row = QHBoxLayout()
    header_row.setSpacing(10)

    avatar = QLabel()
    avatar.setFixedSize(36, 36)
    avatar.setAlignment(Qt.AlignCenter)
    avatar.setScaledContents(True)
    img_p = resource_path("assets", "chef_anime_avatar.png")
    if os.path.exists(img_p):
        avatar.setPixmap(QPixmap(img_p))
    else:
        avatar.setText("👨‍🍳")
    avatar.setStyleSheet(
        f"border: 1.5px solid {_accent_rgba(0.5)}; border-radius: 18px;"
    )
    header_row.addWidget(avatar, 0, Qt.AlignTop)

    info_col = QVBoxLayout()
    info_col.setSpacing(1)
    name_row = QHBoxLayout()
    name_row.setSpacing(6)
    name_lbl = QLabel("Chef Jay AI")
    dark = _is_dark()
    name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {'#F9FAFB' if dark else '#0F172A'};")
    name_row.addWidget(name_lbl)

    status_badge = QLabel("LOCAL AI")
    status_badge.setStyleSheet(
        "font-size: 9px; font-weight: 800; color: #22C55E; background: rgba(34,197,94,0.15);"
        " padding: 1px 6px; border-radius: 6px; border: 1px solid rgba(34,197,94,0.3);"
    )
    name_row.addWidget(status_badge)
    name_row.addStretch()
    info_col.addLayout(name_row)

    sub_info = QLabel("Jayraldine's Catering Assistant")
    sub_info.setStyleSheet("font-size: 11px; color: #9CA3AF;")
    info_col.addWidget(sub_info)

    header_row.addLayout(info_col, 1)
    main_lay.addLayout(header_row)

    div = QFrame()
    div.setObjectName("divider")
    div.setFixedHeight(1)
    main_lay.addWidget(div)

    # Body Content
    if error:
        lbl = QLabel(error)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #DC2626; font-size: 13px;")
        main_lay.addWidget(lbl)
    else:
        lbl = QLabel(answer or "(no answer)")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setStyleSheet(f"font-size: 13px; line-height: 140%; color: {'#F9FAFB' if dark else '#0F172A'};")
        main_lay.addWidget(lbl)

        if chart_spec:
            chart_view = _build_chart(chart_spec)
            if chart_view is not None:
                main_lay.addWidget(chart_view)

        if options:
            opt_col = QVBoxLayout()
            opt_col.setSpacing(6)
            for opt in options:
                label = opt.get("label", "")
                ob = QPushButton(label)
                ob.setObjectName("secondaryButton")
                ob.setCursor(Qt.PointingHandCursor)
                ob.setStyleSheet("text-align: left; padding: 6px 12px; font-size: 12px;")
                if on_option_send:
                    ob.clicked.connect(lambda _, s=opt.get("send", ""): on_option_send(s))
                opt_col.addWidget(ob)
            main_lay.addLayout(opt_col)

        if action:
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)
            btn_row.addStretch()
            dismiss_btn = QPushButton("Cancel")
            dismiss_btn.setObjectName("secondaryButton")
            dismiss_btn.setCursor(Qt.PointingHandCursor)
            confirm_btn = QPushButton("Confirm")
            confirm_btn.setObjectName("primaryButton")
            confirm_btn.setCursor(Qt.PointingHandCursor)
            btn_row.addWidget(dismiss_btn)
            btn_row.addWidget(confirm_btn)
            main_lay.addLayout(btn_row)

            feedback_lbl = QLabel()
            feedback_lbl.setWordWrap(True)
            feedback_lbl.setVisible(False)
            main_lay.addWidget(feedback_lbl)

            def _on_confirm():
                confirm_btn.setEnabled(False)
                dismiss_btn.setEnabled(False)
                confirm_btn.setText("Processing...")
                res = ai_client.execute_action(action)
                confirm_btn.setText("✓ Confirmed")
                dismiss_btn.setVisible(False)
                msg = res.get("message", "Action completed.") if isinstance(res, dict) else str(res)
                is_ok = res.get("ok", True) if isinstance(res, dict) else True
                feedback_lbl.setText(msg)
                feedback_lbl.setStyleSheet(
                    "color: #16A34A; font-weight: 600; font-size: 12px; padding: 6px 10px; "
                    "background: rgba(34,197,94,0.1); border-radius: 8px; border: 1px solid rgba(34,197,94,0.25);"
                    if is_ok else
                    "color: #DC2626; font-weight: 600; font-size: 12px; padding: 6px 10px; "
                    "background: rgba(239,68,68,0.1); border-radius: 8px; border: 1px solid rgba(239,68,68,0.25);"
                )
                feedback_lbl.setVisible(True)
                if on_action_result:
                    on_action_result(res)

            def _on_cancel():
                confirm_btn.setEnabled(False)
                dismiss_btn.setEnabled(False)
                dismiss_btn.setText("Cancelled")
                confirm_btn.setVisible(False)
                feedback_lbl.setText("Cancelled — no changes were made.")
                feedback_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px; padding: 4px 8px;")
                feedback_lbl.setVisible(True)
                if on_action_result:
                    on_action_result({"ok": True, "message": "Cancelled — no changes were made."})

            confirm_btn.clicked.connect(_on_confirm)
            dismiss_btn.clicked.connect(_on_cancel)

    # Footer Action Buttons (Copy, Like)
    footer_row = QHBoxLayout()
    footer_row.setSpacing(6)
    footer_row.addStretch()

    copy_btn = QPushButton("📋 Copy")
    copy_btn.setCursor(Qt.PointingHandCursor)
    copy_btn.setStyleSheet("font-size: 11px; padding: 3px 8px; background: transparent; border: none; color: #9CA3AF;")
    
    def _copy_answer():
        clipboard = QApplication.clipboard()
        clipboard.setText(answer or "")
        copy_btn.setText("✓ Copied!")
        QTimer.singleShot(1500, lambda: copy_btn.setText("📋 Copy"))

    copy_btn.clicked.connect(_copy_answer)
    footer_row.addWidget(copy_btn)

    main_lay.addLayout(footer_row)
    return card


def _build_chart(spec: dict):
    try:
        labels = [str(x) for x in spec.get("labels", [])]
        series_specs = spec.get("series", [])[:2]
        if not labels or not series_specs:
            return None

        from PySide6.QtCharts import (
            QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
        )
        palette = [AccentManager().current, "#94A3B8" if not _is_dark() else "#475569"]
        bar_series = QBarSeries()
        max_val = 1.0
        for i, s in enumerate(series_specs):
            series_name = str(s.get("name", f"Series {i + 1}"))
            values = [float(v) for v in s.get("values", [])][:len(labels)]
            values += [0.0] * (len(labels) - len(values))
            bar_set = QBarSet(series_name)
            color_hex = palette[i % len(palette)]
            bar_set.setColor(QColor(color_hex))
            for v in values:
                bar_set.append(v)

            def _make_hover(bset=bar_set, s_name=series_name, val_list=values, cat_labels=labels, col=color_hex):
                def _on_hover(status: bool, index: int):
                    if status and 0 <= index < len(cat_labels):
                        cat_name = cat_labels[index]
                        val = val_list[index]
                        amt_str = f"₱ {val:,.2f}" if val >= 10 else f"{val:g}"
                        from PySide6.QtGui import QCursor
                        from PySide6.QtWidgets import QToolTip
                        QToolTip.showText(
                            QCursor.pos(),
                            f"<b style='color:{col};'>{cat_name}</b> ({s_name})<br>"
                            f"Amount: <b>{amt_str}</b>"
                        )
                    else:
                        from PySide6.QtWidgets import QToolTip
                        QToolTip.hideText()
                return _on_hover

            bar_set.hovered.connect(_make_hover())
            max_val = max(max_val, *values) if values else max_val
            bar_series.append(bar_set)

        label_color = QColor("#5B6B84" if not _is_dark() else "#9CA3AF")
        chart = QChart()
        if spec.get("title"):
            chart.setTitle(str(spec["title"]))
            chart.setTitleBrush(QColor("#101828" if not _is_dark() else "#F9FAFB"))
        chart.addSeries(bar_series)
        chart.setBackgroundBrush(Qt.transparent)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.legend().setLabelColor(label_color)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        axis_x.setLabelsColor(label_color)
        axis_x.setGridLineVisible(False)
        axis_x.setLinePenColor(Qt.transparent)
        chart.addAxis(axis_x, Qt.AlignBottom)
        bar_series.attachAxis(axis_x)

        upper = max(max_val * 1.15, 1.0)
        target_ticks = 5
        raw_step = upper / (target_ticks - 1)
        magnitude = 10 ** int(math.floor(math.log10(max(raw_step, 1))))
        residual = raw_step / magnitude
        if residual <= 1.5:
            clean_step = 1.0 * magnitude
        elif residual <= 3.0:
            clean_step = 2.5 * magnitude
        elif residual <= 7.0:
            clean_step = 5.0 * magnitude
        else:
            clean_step = 10.0 * magnitude

        num_steps = max(1, int(math.ceil(upper / clean_step)))
        final_max = num_steps * clean_step

        from PySide6.QtCharts import QCategoryAxis
        axis_y = QCategoryAxis()
        axis_y.setRange(0, final_max)

        for i in range(num_steps + 1):
            val = clean_step * i
            lbl = f"₱{val:,.0f}"
            axis_y.append(lbl, val)

        axis_y.setLabelsColor(label_color)
        axis_y.setGridLineColor(QColor("#EDF1F7" if not _is_dark() else "#243244"))
        axis_y.setLinePenColor(Qt.transparent)
        chart.addAxis(axis_y, Qt.AlignLeft)
        bar_series.attachAxis(axis_y)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setStyleSheet("background: transparent;")
        view.setMinimumHeight(220)
        return view
    except Exception:
        return None


class GlobalAIChatDrawer(QFrame):
    """Floating AI Popover Drawer accessible everywhere in the app."""
    def __init__(self, parent=None, mascot_widget=None):
        super().__init__(parent)
        self.setObjectName("modalCard")
        self.setFixedWidth(520)
        self.setFixedHeight(620)
        self.hide()

        self._busy = False
        self._thread = None
        self._mascot_widget = mascot_widget

        # ESC key shortcut to close drawer
        self._shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self._shortcut_esc.activated.connect(self.hide)

        # Skip QGraphicsDropShadowEffect — triggers full software rasterization on Intel HD GPUs.

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header Bar
        head = QHBoxLayout()
        head.setSpacing(10)

        avatar = QLabel()
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setScaledContents(True)
        img_p = resource_path("assets", "chef_anime_avatar.png")
        if os.path.exists(img_p):
            avatar.setPixmap(QPixmap(img_p))
        else:
            avatar.setText("👨‍🍳")
        avatar.setStyleSheet(
            f"border: 1.5px solid {_accent_rgba(0.5)}; border-radius: 16px;"
        )
        head.addWidget(avatar)

        t_col = QVBoxLayout()
        t_col.setSpacing(0)
        title = QLabel("Chef Jay AI — Global Assistant")
        title.setStyleSheet("font-size: 13px; font-weight: 700;")
        sub = QLabel("Online • Ask anything about your business")
        sub.setStyleSheet("font-size: 11px; color: #22C55E;")
        t_col.addWidget(title)
        t_col.addWidget(sub)
        head.addLayout(t_col, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("Close Chat (Esc)")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(225,29,72,0.15); color: #E11D48; border: 1px solid rgba(225,29,72,0.3); "
            "border-radius: 14px; font-weight: 800; font-size: 13px; }"
            "QPushButton:hover { background: #E11D48; color: #FFFFFF; }"
        )
        close_btn.clicked.connect(self.hide)
        head.addWidget(close_btn)

        layout.addLayout(head)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        # Suggested Prompt Chips
        chip_scroll = QScrollArea()
        chip_scroll.setWidgetResizable(True)
        chip_scroll.setFrameShape(QFrame.NoFrame)
        chip_scroll.setFixedHeight(36)
        chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        chip_w = QWidget()
        chip_row = QHBoxLayout(chip_w)
        chip_row.setContentsMargins(0, 0, 0, 0)
        chip_row.setSpacing(6)

        prompts = [
            "💡 Business Suggestions",
            "📊 Today's Briefing",
            "👥 Top Customers",
            "💳 Unpaid Invoices",
            "📈 Revenue Comparison",
            "📅 Upcoming Bookings",
        ]
        for p_text in prompts:
            btn = QPushButton(p_text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"background: {_accent_rgba(0.08)}; color: {AccentManager().current}; "
                f"border: 1px solid {_accent_rgba(0.25)}; border-radius: 12px; padding: 4px 10px; "
                "font-size: 11px; font-weight: 600;"
            )
            btn.clicked.connect(lambda _, q=p_text[2:].strip(): self.ask(q))
            chip_row.addWidget(btn)

        chip_row.addStretch()
        chip_scroll.setWidget(chip_w)
        layout.addWidget(chip_scroll)

        # Feed Area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._feed_w = QWidget()
        self._feed = QVBoxLayout(self._feed_w)
        self._feed.setContentsMargins(0, 0, 4, 0)
        self._feed.setSpacing(10)
        self._feed.addStretch()
        self._scroll.setWidget(self._feed_w)
        layout.addWidget(self._scroll, 1)

        # Input Card
        in_card = QFrame()
        in_card.setObjectName("card")
        in_lay = QHBoxLayout(in_card)
        in_lay.setContentsMargins(10, 6, 8, 6)
        in_lay.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Chef Jay AI anything...")
        self._input.setStyleSheet("border: none; background: transparent; font-size: 13px;")
        self._input.returnPressed.connect(lambda: self.ask(self._input.text()))
        in_lay.addWidget(self._input, 1)

        self._btn_ask = QPushButton("Ask")
        self._btn_ask.setObjectName("primaryButton")
        self._btn_ask.setCursor(Qt.PointingHandCursor)
        self._btn_ask.setFixedHeight(30)
        self._btn_ask.clicked.connect(lambda: self.ask(self._input.text()))
        in_lay.addWidget(self._btn_ask)

        layout.addWidget(in_card)

        # Welcome note
        welcome_card = build_ai_card(
            "Hello! I'm Chef Jay AI. You can ask me questions from any page in the app! "
            "Try asking about sales, top customers, or pending follow-ups."
        )
        self._add_to_feed(welcome_card)

        try:
            from utils.reminder_manager import reminder_manager
            reminder_manager().alarm_fired.connect(self._on_alarm_fired)
        except Exception:
            pass

    def _on_alarm_fired(self, entry: dict):
        msg = entry.get("message", "Alarm")
        target_dt = entry.get("target_dt")
        time_str = target_dt.strftime("%I:%M %p").lstrip("0") if target_dt else datetime.now().strftime("%I:%M %p")
        ans = (
            f"⏰ **ALARM TRIGGERED** ({time_str})\n\n"
            f"• Note: \"{msg}\"\n"
            f"• Status: Completed\n\n"
            f"What would you like to do?"
        )
        options = [
            {"label": "Snooze 5 mins", "send": "snooze 5 minutes"},
            {"label": "Snooze 10 mins", "send": "snooze 10 minutes"},
            {"label": "Dismiss", "send": "ok"}
        ]
        card = build_ai_card(ans, None, options=options, on_option_send=self.ask)
        self._add_to_feed(card)
        if self._mascot_widget and hasattr(self._mascot_widget, "mascot"):
            self._mascot_widget.mascot.set_state("surprised")

    def _add_to_feed(self, w: QWidget):
        self._feed.insertWidget(self._feed.count() - 1, w)
        QTimer.singleShot(60, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()))

    def ask(self, question: str):
        question = (question or "").strip()
        if not question or self._busy:
            return
        self._input.clear()
        self._add_to_feed(build_user_bubble(question))

        self._busy = True
        self._btn_ask.setEnabled(False)
        self._btn_ask.setText("Thinking...")

        if self._mascot_widget and hasattr(self._mascot_widget, "mascot"):
            self._mascot_widget.mascot.set_state("thinking")

        self._stop_thread()
        self._thread = QThread()
        self._worker = _AskWorker(question)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_result)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _stop_thread(self):
        if getattr(self, "_thread", None) is not None:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(500)
            except Exception:
                pass
            self._thread = None
        if getattr(self, "_worker", None) is not None:
            self._worker = None

    def hideEvent(self, event):
        self._stop_thread()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._stop_thread()
        super().closeEvent(event)

    def _on_result(self, result: dict):
        self._busy = False
        self._btn_ask.setEnabled(True)
        self._btn_ask.setText("Ask")

        if self._mascot_widget and hasattr(self._mascot_widget, "mascot"):
            self._mascot_widget.mascot.set_state("confused" if result.get("error") else "happy")

        def _on_action_done(res: dict):
            msg = res.get("message", "Action completed.") if isinstance(res, dict) else str(res)
            is_ok = res.get("ok", True) if isinstance(res, dict) else True
            if self._mascot_widget and hasattr(self._mascot_widget, "mascot"):
                self._mascot_widget.mascot.set_state("happy" if is_ok else "confused")
            if is_ok:
                try:
                    from utils.signals import app_events
                    app_events().data_changed.emit()
                except Exception:
                    pass
            # Post a follow-up card confirming the action execution in conversational style
            followup_card = build_ai_card(msg, None, error="" if is_ok else msg, on_option_send=self.ask)
            self._add_to_feed(followup_card)

        card = build_ai_card(
            result.get("answer", ""), result.get("chart"),
            result.get("error", ""), result.get("action"),
            result.get("options"), on_option_send=self.ask,
            on_action_result=_on_action_done
        )
        self._add_to_feed(card)

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self._input.setFocus()


class DraggableMascotWidget(QWidget):
    """Floating, draggable Mascot widget overlaid on MainWindow."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 96)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._drag_pos = None
        self._user_moved = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.mascot = ChefMascot(self, size=64)
        layout.addWidget(self.mascot)

        pill_col = QVBoxLayout()
        pill_col.setSpacing(2)
        pill_col.addStretch()

        badge = QLabel("Chef Jay AI")
        badge.setStyleSheet(
            f"background: {AccentManager().current}; color: #FFFFFF; font-size: 10px; "
            "font-weight: 800; border-radius: 8px; padding: 3px 7px;"
        )
        pill_col.addWidget(badge)
        pill_col.addStretch()

        layout.addLayout(pill_col)

        self.drawer = GlobalAIChatDrawer(parent, mascot_widget=self)
        self.mascot.clicked.connect(self._on_mascot_click)

    def _update_drawer_position(self):
        if not self.drawer or not self.parentWidget():
            return
        parent_w = self.parentWidget().width()
        parent_h = self.parentWidget().height()
        drawer_w = self.drawer.width()
        drawer_h = self.drawer.height()

        # Position drawer cleanly beside / above mascot without overlapping
        # Default: Place drawer to the left of mascot
        x = self.x() - drawer_w - 12
        y = self.y() - drawer_h + self.height()

        # If too far left, place drawer to the right of mascot
        if x < 20:
            x = self.x() + self.width() + 12

        # Clamp x within window margins
        if x < 20:
            x = 20
        if x + drawer_w > parent_w - 20:
            x = parent_w - drawer_w - 20

        # Clamp y within window margins
        if y < 20:
            y = 20
        if y + drawer_h > parent_h - 20:
            y = parent_h - drawer_h - 20

        self.drawer.move(x, y)
        self.drawer.raise_()
        self.raise_()  # ALWAYS KEEP MASCOT ON TOP

    def _on_mascot_click(self):
        if not self.drawer.isVisible():
            self._update_drawer_position()
            self.drawer.show()
            self.drawer.raise_()
            self.raise_()  # ALWAYS KEEP MASCOT ON TOP
            self.drawer._input.setFocus()
        else:
            self.drawer.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.raise_()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self._user_moved = True
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            if self.parentWidget():
                max_x = self.parentWidget().width() - self.width()
                max_y = self.parentWidget().height() - self.height()
                clamped_x = max(0, min(new_pos.x(), max_x))
                clamped_y = max(0, min(new_pos.y(), max_y))
                self.move(clamped_x, clamped_y)
            else:
                self.move(new_pos)

            if self.drawer and self.drawer.isVisible():
                self._update_drawer_position()

            if hasattr(self, "mascot") and hasattr(self.mascot, "_quote_bubble") and self.mascot._quote_bubble.isVisible():
                self.mascot._quote_bubble.reposition()

            self.raise_()  # ALWAYS KEEP MASCOT ON TOP
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
