"""
Shared visual design system for the Tablet App — one place to tune colors,
spacing, and component styles instead of ad hoc inline styles scattered
across every screen.
"""

BG = "#0B1220"
CARD = "#141C2E"
CARD_ELEVATED = "#1A2438"
BORDER = "#263248"
INPUT_BG = "#1A2438"

TEXT = "#F8FAFC"
TEXT_MUTED = "#8B98AF"
TEXT_FAINT = "#64748B"

ACCENT = "#E11D48"
ACCENT_HOVER = "#F43F5E"
ACCENT_PRESS = "#BE123C"

SUCCESS = "#22C55E"
WARNING = "#F59E0B"
DANGER = "#EF4444"
INFO = "#38BDF8"

RADIUS = 14
RADIUS_SM = 10

FONT_FAMILY = "'Segoe UI', 'Noto Sans', sans-serif"

GLOBAL_QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: {FONT_FAMILY};
    font-size: 14px;
    border: none;
}}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QMessageBox, QInputDialog, QFileDialog {{ background: {CARD}; }}
QLabel {{ color: {TEXT}; background: transparent; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {TEXT_FAINT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QTextBrowser {{
    font-size: 16px;
    padding: 12px 14px;
    border-radius: {RADIUS_SM}px;
    border: 1.5px solid {BORDER};
    background: {INPUT_BG};
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1.5px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox QAbstractItemView {{
    background: {CARD_ELEVATED}; color: {TEXT}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT}; padding: 4px;
}}
QDateEdit::drop-down, QTimeEdit::drop-down {{ border: none; width: 28px; }}
QCalendarWidget {{ background: {CARD_ELEVATED}; color: {TEXT}; }}
QCalendarWidget QToolButton {{ color: {TEXT}; background: transparent; }}
QCalendarWidget QAbstractItemView:enabled {{ background: {CARD}; color: {TEXT}; selection-background-color: {ACCENT}; }}

QRadioButton, QCheckBox {{
    color: {TEXT}; font-size: 15px; spacing: 10px; padding: 6px 2px;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 22px; height: 22px; border-radius: 6px; border: 2px solid {BORDER}; background: {INPUT_BG};
}}
QRadioButton::indicator {{ border-radius: 11px; }}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
    background: {ACCENT}; border: 2px solid {ACCENT};
}}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {{ border: 2px solid {ACCENT}; }}

QPushButton#Primary {{
    font-size: 16px; font-weight: 700; padding: 15px 26px; border-radius: {RADIUS_SM}px;
    background: {ACCENT}; color: white; border: none;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_PRESS}; }}
QPushButton#Primary:disabled {{ background: #3A4356; color: #6B7688; }}

QPushButton#Secondary {{
    font-size: 15px; font-weight: 600; padding: 13px 22px; border-radius: {RADIUS_SM}px;
    background: {CARD_ELEVATED}; color: {TEXT}; border: 1.5px solid {BORDER};
}}
QPushButton#Secondary:hover {{ border: 1.5px solid {TEXT_FAINT}; background: #202B42; }}
QPushButton#Secondary:pressed {{ background: {BG}; }}

QPushButton#Ghost {{
    font-size: 13px; font-weight: 600; padding: 8px 14px; border-radius: 8px;
    background: transparent; color: {TEXT_MUTED}; border: 1px solid {BORDER};
}}
QPushButton#Ghost:hover {{ color: {TEXT}; border: 1px solid {TEXT_FAINT}; }}

QPushButton#Danger {{
    font-size: 13px; font-weight: 600; padding: 8px 14px; border-radius: 8px;
    background: transparent; color: {DANGER}; border: 1.5px solid {DANGER};
}}
QPushButton#Danger:hover {{ background: rgba(239,68,68,0.12); }}
"""


_card_counter = [0]


def card_frame_style(elevated: bool = False, accent_border: bool = False) -> str:
    """DEPRECATED for direct use on QFrame.setStyleSheet(): an unselected
    (bare-property) stylesheet on a widget instance cascades to ALL
    descendant widgets in Qt's QSS engine — including QLabel, since QLabel
    derives from QFrame and QSS type selectors match by inheritance. Use
    make_card() instead, which scopes the rule to an objectName so it only
    paints the card frame itself, never its children."""
    bg = CARD_ELEVATED if elevated else CARD
    border = ACCENT if accent_border else BORDER
    return f"background: {bg}; border-radius: {RADIUS}px; border: 1px solid {border};"


def style_card(frame, elevated: bool = False, accent_border: bool = False) -> None:
    """Applies card styling to `frame` scoped so it can never leak onto
    child widgets (see card_frame_style docstring for why that matters)."""
    _card_counter[0] += 1
    name = f"ThemeCard{_card_counter[0]}"
    frame.setObjectName(name)
    bg = CARD_ELEVATED if elevated else CARD
    border = ACCENT if accent_border else BORDER
    frame.setStyleSheet(f"QFrame#{name} {{ background: {bg}; border-radius: {RADIUS}px; border: 1px solid {border}; }}")


def heading_style(size: int = 22) -> str:
    return f"font-size: {size}px; font-weight: 800; color: {TEXT};"


def subtitle_style(size: int = 13) -> str:
    return f"font-size: {size}px; color: {TEXT_MUTED};"


def pill_style(color: str) -> str:
    return (
        f"font-size: 12px; font-weight: 700; padding: 5px 12px; border-radius: 10px; "
        f"background: rgba(255,255,255,0.06); color: {color}; border: 1px solid {color};"
    )


STATUS_COLORS = {"Paid": SUCCESS, "Partial": WARNING, "Unpaid": DANGER}
