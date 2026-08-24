"""
AI Assistant page — ask business questions in plain language
("compare August last year vs this year") and get a narrative answer
plus a locally-rendered comparison chart.

The AI only ever sees aggregated numbers (utils/ai_client.build_data_pack);
all charts are drawn locally with QtCharts from the spec it returns.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QLineEdit, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QMargins, QPoint, QTimer
from PySide6.QtGui import QColor, QPainter

from utils.theme import ThemeManager
from utils.accent import AccentManager
import utils.ai_client as ai_client
from components.mascot import ChefMascot
from components.global_ai_floating import build_user_bubble, build_ai_card

# Longer answers (ledger summaries, communication history, daily briefings)
# are a single long QLabel line. Without a cap, QLabel's wordWrap-aware
# sizeHint still reports its *unwrapped* natural width to the layout, which
# then demands that width all the way up to the page/window — this is what
# was making the whole AI page (and window) grow wider. Capping the label's
# width forces it to wrap and grow vertically instead.
_ANSWER_MAX_WIDTH = 760

_SUGGESTIONS = [
    "Target Sales Comparison (Target vs Actual)",
    "Compare revenue last year vs this year",
    "Which month earned the most this year?",
    "Who are our top customers?",
    "Any unpaid invoices I should follow up?",
    "Approve a pending booking",
    "Any follow-ups due today?",
    "Show my notifications",
    "List all customers",
    "List bookings this week",
    "List invoices this month",
]


def _is_light():
    return not ThemeManager().is_dark()


class _AskWorker(QObject):
    finished = Signal(dict)

    def __init__(self, question: str):
        super().__init__()
        self._question = question

    def run(self):
        self.finished.emit(ai_client.ask(self._question))


class _BriefingWorker(QObject):
    finished = Signal(dict)

    def run(self):
        try:
            self.finished.emit(ai_client.daily_briefing())
        except Exception:
            self.finished.emit({})


class AIPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainBackground")
        self._thread = None
        self._busy = False

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────────────────────
        head_row = QHBoxLayout()
        head_row.setSpacing(14)

        # The mascot itself floats freely (and is draggable) over the whole
        # page — it is NOT layout-managed. This invisible spacer just reserves
        # its default footprint in the header so the title keeps its usual
        # indentation.
        mascot_anchor = QWidget(self)
        mascot_anchor.setFixedSize(84, 84)
        mascot_anchor.setStyleSheet("background: transparent;")
        head_row.addWidget(mascot_anchor, 0, Qt.AlignTop)
        self._mascot_anchor = mascot_anchor

        head = QVBoxLayout()
        head.setSpacing(2)
        title = QLabel("AI Assistant")
        title.setObjectName("pageTitle")
        sub = QLabel("Ask anything about the business — bookings, customers, expenses, "
                     "comparisons, trends — or how to use the app. Answers come straight "
                     "from your data, fully offline.")
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        head.addWidget(title)
        head.addWidget(sub)
        head_row.addLayout(head, 1)
        root.addLayout(head_row)

        # ── Suggestion chips ────────────────────────────────────────────────
        chip_scroll = QScrollArea(self)
        chip_scroll.setWidgetResizable(True)
        chip_scroll.setFrameShape(QFrame.NoFrame)
        chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        chip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        chip_scroll.setFixedHeight(46)
        chip_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        chip_w = QWidget()
        chip_w.setStyleSheet("background: transparent;")
        chip_row = QHBoxLayout(chip_w)
        chip_row.setContentsMargins(0, 0, 0, 0)
        chip_row.setSpacing(8)
        for s in _SUGGESTIONS:
            chip = QPushButton(s)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setObjectName("pageButton")
            chip.clicked.connect(lambda _, q=s: self._ask(q))
            chip_row.addWidget(chip)
        chip_row.addStretch()
        chip_scroll.setWidget(chip_w)
        root.addWidget(chip_scroll)

        # ── Conversation area ───────────────────────────────────────────────
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._feed_w = QWidget()
        self._feed_w.setStyleSheet("background: transparent;")
        self._feed = QVBoxLayout(self._feed_w)
        self._feed.setContentsMargins(0, 0, 8, 0)
        self._feed.setSpacing(14)
        self._feed.addStretch()
        self._scroll.setWidget(self._feed_w)
        root.addWidget(self._scroll, 1)

        # ── Input bar ───────────────────────────────────────────────────────
        input_card = QFrame(self)
        input_card.setObjectName("card")
        in_lay = QHBoxLayout(input_card)
        in_lay.setContentsMargins(16, 10, 12, 10)
        in_lay.setSpacing(10)

        self._input = QLineEdit()
        self._input.setPlaceholderText(
            'e.g. "Compare August last year vs this year"')
        self._input.setStyleSheet("border: none; background: transparent; font-size: 14px;")
        self._input.returnPressed.connect(lambda: self._ask(self._input.text()))
        in_lay.addWidget(self._input, 1)

        self._btn_ask = QPushButton("Ask")
        self._btn_ask.setObjectName("primaryButton")
        self._btn_ask.setCursor(Qt.PointingHandCursor)
        self._btn_ask.setMinimumWidth(90)
        self._btn_ask.clicked.connect(lambda: self._ask(self._input.text()))
        in_lay.addWidget(self._btn_ask)
        root.addWidget(input_card)

        self._add_note(
            "Built-in assistant — it studies your live system data (bookings, billing, "
            "expenses, customers, reports) and answers instantly, fully offline. "
            "Ask in English or Bisaya. Type \"help\" to see what it can do."
        )

        # Floating, draggable mascot — a direct child of the page (not the
        # scroll feed), so it stays put on screen while the conversation
        # scrolls underneath it. Placed after everything else so it's on top.
        self._mascot = ChefMascot(self, size=84)
        self._mascot.clicked.connect(lambda: (self._input.setFocus(), self._input.selectAll()))
        self._mascot.resetRequested.connect(self._reposition_mascot)
        self._mascot.show()
        QTimer.singleShot(0, self._reposition_mascot)

        from utils.reminder_manager import reminder_manager
        reminder_manager().alarm_fired.connect(self._on_alarm_fired)

        self._start_briefing()

    def __del__(self):
        try:
            self._stop_briefing_thread()
            self._stop_ask_thread()
        except Exception:
            pass

    def _reposition_mascot(self):
        """Snap the mascot to its default header spot, unless the user has
        already dragged it — then just keep it inside the page bounds."""
        if self._mascot.has_been_moved():
            self._mascot.clamp_to_parent()
        else:
            anchor_pos = self._mascot_anchor.mapTo(self, QPoint(0, 0))
            self._mascot.move(anchor_pos)
        self._mascot.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_mascot"):
            self._reposition_mascot()

    def _start_briefing(self):
        """Proactively surface today's events, due/overdue follow-ups, unread
        notifications, and unpaid invoices as soon as the page opens."""
        self._stop_briefing_thread()
        self._briefing_thread = QThread()
        self._briefing_worker = _BriefingWorker()
        self._briefing_worker.moveToThread(self._briefing_thread)
        self._briefing_thread.started.connect(self._briefing_worker.run)
        self._briefing_worker.finished.connect(self._on_briefing)
        self._briefing_worker.finished.connect(self._briefing_thread.quit)
        self._briefing_worker.finished.connect(self._briefing_worker.deleteLater)
        self._briefing_thread.finished.connect(self._briefing_thread.deleteLater)
        self._briefing_thread.start()

    def _on_briefing(self, result: dict):
        answer = (result or {}).get("answer")
        if answer:
            self._add_answer_card(answer, None, "")
            self._mascot.set_state("happy")

    # ── Feed helpers ─────────────────────────────────────────────────────────

    def _add_to_feed(self, w: QWidget):
        self._feed.insertWidget(self._feed.count() - 1, w)
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()))

    def _add_note(self, text: str):
        card = QFrame()
        card.setObjectName("cardElevated")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lbl = QLabel(text)
        lbl.setObjectName("subtitle")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        self._add_to_feed(card)

    def _add_question_bubble(self, question: str):
        self._add_to_feed(build_user_bubble(question))

    def _add_answer_card(self, answer: str, chart_spec: dict | None,
                         error: str = "", action: dict | None = None,
                         options: list | None = None):
        def _on_action_done(res: dict):
            msg = res.get("message", "Action completed.") if isinstance(res, dict) else str(res)
            is_ok = res.get("ok", True) if isinstance(res, dict) else True
            if hasattr(self, "_mascot"):
                self._mascot.set_state("happy" if is_ok else "confused")
            if is_ok:
                try:
                    from utils.signals import app_events
                    app_events().data_changed.emit()
                except Exception:
                    pass
            self._add_answer_card(msg, None, error="" if is_ok else msg)

        card = build_ai_card(answer, chart_spec, error, action, options,
                              on_option_send=self._ask,
                              on_action_result=_on_action_done if action else None)
        self._add_to_feed(card)

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
        self._add_answer_card(ans, None, options=options)
        if hasattr(self, "_mascot"):
            self._mascot.set_state("surprised")

    def _build_chart(self, spec: dict):
        try:
            labels = [str(x) for x in spec.get("labels", [])]
            series_specs = spec.get("series", [])[:2]
            if not labels or not series_specs:
                return None

            from PySide6.QtCharts import (
                QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
            )
            palette = [AccentManager().current, "#94A3B8" if _is_light() else "#475569"]
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

            label_color = QColor("#5B6B84" if _is_light() else "#9CA3AF")
            chart = QChart()
            if spec.get("title"):
                chart.setTitle(str(spec["title"]))
                chart.setTitleBrush(QColor("#101828" if _is_light() else "#F9FAFB"))
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
            axis_y.setGridLineColor(QColor("#EDF1F7" if _is_light() else "#243244"))
            axis_y.setLinePenColor(Qt.transparent)
            chart.addAxis(axis_y, Qt.AlignLeft)
            bar_series.attachAxis(axis_y)

            view = QChartView(chart)
            view.setRenderHint(QPainter.Antialiasing)
            view.setStyleSheet("background: transparent;")
            view.setMinimumHeight(260)
            return view
        except (TypeError, ValueError):
            return None

    def _stop_briefing_thread(self):
        if getattr(self, "_briefing_thread", None) is not None:
            try:
                if self._briefing_thread.isRunning():
                    self._briefing_thread.quit()
                    self._briefing_thread.wait(500)
            except Exception:
                pass
            self._briefing_thread = None
        self._briefing_worker = None

    def _stop_ask_thread(self):
        if getattr(self, "_thread", None) is not None:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(500)
            except Exception:
                pass
            self._thread = None
        self._worker = None

    def hideEvent(self, event):
        self._stop_briefing_thread()
        self._stop_ask_thread()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._stop_briefing_thread()
        self._stop_ask_thread()
        super().closeEvent(event)

    def _ask(self, question: str):
        question = (question or "").strip()
        if not question or self._busy:
            return
        self._input.clear()
        self._add_question_bubble(question)

        self._busy = True
        self._btn_ask.setEnabled(False)
        self._btn_ask.setText("Thinking…")
        self._mascot.set_state("thinking")

        self._stop_ask_thread()
        self._thread = QThread()
        self._worker = _AskWorker(question)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_result)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_result(self, result: dict):
        self._busy = False
        self._btn_ask.setEnabled(True)
        self._btn_ask.setText("Ask")
        self._mascot.set_state("confused" if result.get("error") else "happy")
        self._add_answer_card(
            result.get("answer", ""), result.get("chart"),
            result.get("error", ""), result.get("action"),
            result.get("options")
        )
