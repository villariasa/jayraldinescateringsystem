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
from PySide6.QtCore import Qt, QThread, QObject, Signal, QMargins
from PySide6.QtGui import QColor, QPainter

from utils.theme import ThemeManager
import utils.ai_client as ai_client

# Longer answers (ledger summaries, communication history, daily briefings)
# are a single long QLabel line. Without a cap, QLabel's wordWrap-aware
# sizeHint still reports its *unwrapped* natural width to the layout, which
# then demands that width all the way up to the page/window — this is what
# was making the whole AI page (and window) grow wider. Capping the label's
# width forces it to wrap and grow vertically instead.
_ANSWER_MAX_WIDTH = 760

_SUGGESTIONS = [
    "Compare revenue last year vs this year",
    "Which month earned the most this year?",
    "Who are our top customers?",
    "Any unpaid invoices I should follow up?",
    "Approve a pending booking",
    "Any follow-ups due today?",
    "Show my notifications",
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
        root.setContentsMargins(40, 40, 40, 24)
        root.setSpacing(20)

        # ── Header ──────────────────────────────────────────────────────────
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
        root.addLayout(head)

        # ── Suggestion chips ────────────────────────────────────────────────
        chip_scroll = QScrollArea(self)
        chip_scroll.setWidgetResizable(True)
        chip_scroll.setFrameShape(QFrame.NoFrame)
        chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        chip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        chip_scroll.setFixedHeight(44)
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

        self._start_briefing()

    def _start_briefing(self):
        """Proactively surface today's events, due/overdue follow-ups, unread
        notifications, and unpaid invoices as soon as the page opens."""
        self._briefing_thread = QThread()
        self._briefing_worker = _BriefingWorker()
        self._briefing_worker.moveToThread(self._briefing_thread)
        self._briefing_thread.started.connect(self._briefing_worker.run)
        self._briefing_worker.finished.connect(self._on_briefing)
        self._briefing_worker.finished.connect(self._briefing_thread.quit)
        self._briefing_thread.start()

    def _on_briefing(self, result: dict):
        answer = (result or {}).get("answer")
        if answer:
            self._add_answer_card(answer, None, "")

    # ── Feed helpers ─────────────────────────────────────────────────────────

    def _add_to_feed(self, w: QWidget):
        self._feed.insertWidget(self._feed.count() - 1, w)
        from PySide6.QtCore import QTimer
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
        row = QHBoxLayout()
        row.addStretch()
        bubble = QLabel(question)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(560)
        bubble.setStyleSheet(
            "background: #E11D48; color: #FFFFFF; border-radius: 12px;"
            " padding: 10px 16px; font-size: 13px; font-weight: 600;"
        )
        row.addWidget(bubble)
        wrap = QWidget()
        wrap.setLayout(row)
        self._add_to_feed(wrap)

    def _add_answer_card(self, answer: str, chart_spec: dict | None,
                         error: str = "", action: dict | None = None,
                         options: list | None = None):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        if error:
            lbl = QLabel(error)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #DC2626; font-size: 13px;")
            lay.addWidget(lbl)
        else:
            lbl = QLabel(answer or "(no answer)")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl.setStyleSheet("font-size: 13px; line-height: 140%;")
            lay.addWidget(lbl)
            if chart_spec:
                chart_view = self._build_chart(chart_spec)
                if chart_view is not None:
                    lay.addWidget(chart_view)
            if options:
                opt_col = QVBoxLayout()
                opt_col.setSpacing(6)
                opt_buttons = []

                def _pick(send_text):
                    for ob in opt_buttons:
                        ob.setEnabled(False)
                    self._ask(send_text)

                for opt in options:
                    label = opt.get("label", "")
                    ob = QPushButton(label)
                    ob.setObjectName("secondaryButton")
                    ob.setCursor(Qt.PointingHandCursor)
                    ob.setStyleSheet("text-align: left; padding: 8px 14px;")
                    if len(label) > 90:
                        ob.setText(label[:87] + "...")
                        ob.setToolTip(label)
                    ob.clicked.connect(lambda _, s=opt.get("send", ""): _pick(s))
                    opt_buttons.append(ob)
                    opt_col.addWidget(ob)
                lay.addLayout(opt_col)
            if action:
                btn_row = QHBoxLayout()
                btn_row.setSpacing(10)
                btn_row.addStretch()
                dismiss_btn = QPushButton("Cancel")
                dismiss_btn.setObjectName("secondaryButton")
                dismiss_btn.setCursor(Qt.PointingHandCursor)
                confirm_btn = QPushButton("Confirm")
                confirm_btn.setObjectName(
                    "dangerFilledButton"
                    if action.get("status") == "CANCELLED" or action.get("risk") == "high"
                    else "primaryButton")
                confirm_btn.setCursor(Qt.PointingHandCursor)
                confirm_btn.setMinimumWidth(110)
                btn_row.addWidget(dismiss_btn)
                btn_row.addWidget(confirm_btn)
                lay.addLayout(btn_row)

                def _finish(text_val):
                    confirm_btn.setEnabled(False)
                    dismiss_btn.setEnabled(False)
                    confirm_btn.setText(text_val)

                def _on_confirm():
                    result = ai_client.execute_action(action)
                    _finish("Confirmed")
                    self._add_answer_card(
                        result["message"] if result["ok"] else "",
                        None, "" if result["ok"] else result["message"])

                def _on_dismiss():
                    _finish("Confirm")
                    dismiss_btn.setText("Cancelled")
                    self._add_answer_card("Okay, I didn't change anything.", None)

                confirm_btn.clicked.connect(_on_confirm)
                dismiss_btn.clicked.connect(_on_dismiss)
        self._add_to_feed(card)

    def _build_chart(self, spec: dict):
        try:
            labels = [str(x) for x in spec.get("labels", [])]
            series_specs = spec.get("series", [])[:2]
            if not labels or not series_specs:
                return None

            from PySide6.QtCharts import (
                QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
            )
            palette = ["#E11D48", "#94A3B8" if _is_light() else "#475569"]
            bar_series = QBarSeries()
            max_val = 1.0
            for i, s in enumerate(series_specs):
                values = [float(v) for v in s.get("values", [])][:len(labels)]
                values += [0.0] * (len(labels) - len(values))
                bar_set = QBarSet(str(s.get("name", f"Series {i + 1}")))
                bar_set.setColor(QColor(palette[i % len(palette)]))
                for v in values:
                    bar_set.append(v)
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

            axis_y = QValueAxis()
            axis_y.setRange(0, max_val * 1.15)
            axis_y.setLabelFormat("P%.0f")
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

    # ── Ask flow ─────────────────────────────────────────────────────────────

    def _ask(self, question: str):
        question = (question or "").strip()
        if not question or self._busy:
            return
        self._input.clear()
        self._add_question_bubble(question)

        self._busy = True
        self._btn_ask.setEnabled(False)
        self._btn_ask.setText("Thinking…")

        self._thread = QThread()
        self._worker = _AskWorker(question)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_result)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_result(self, result: dict):
        self._busy = False
        self._btn_ask.setEnabled(True)
        self._btn_ask.setText("Ask")
        self._add_answer_card(
            result.get("answer", ""), result.get("chart"),
            result.get("error", ""), result.get("action"),
            result.get("options")
        )
