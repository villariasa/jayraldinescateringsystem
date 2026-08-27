"""
Modern Animated Terms & Conditions Modal for Jayraldine's Catering Tablet Kiosk.
Displays before starting an order to ensure full data privacy and policy agreement.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QTextBrowser, QFrame, QGraphicsOpacityEffect, QWidget
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor

import utils.terms as terms
from ui import theme, icons


class TermsModal(QDialog):
    """Sleek touch-optimized modal dialog for Terms & Conditions agreement."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(880, 680)

        self._has_scrolled_to_bottom = False
        self._build_ui()
        self._setup_animation()

    def _build_ui(self):
        # Root backdrop
        backdrop = QVBoxLayout(self)
        backdrop.setContentsMargins(20, 20, 20, 20)
        backdrop.setAlignment(Qt.AlignCenter)

        # Dialog Card Container
        card = QFrame()
        card.setObjectName("ModalCard")
        card.setStyleSheet(f"""
            QFrame#ModalCard {{
                background-color: {theme.CARD};
                border: 2px solid {theme.BORDER_LIGHT};
                border-radius: 18px;
            }}
        """)
        
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(32, 28, 32, 28)
        card_lay.setSpacing(14)

        # Header Badge & Title
        header_lay = QVBoxLayout()
        header_lay.setSpacing(6)

        badge_row = QHBoxLayout()
        tag = QLabel("OFFICIAL CATERING AGREEMENT")
        tag.setStyleSheet("""
            background-color: rgba(245, 158, 11, 0.15);
            color: #F59E0B;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1px;
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid rgba(245, 158, 11, 0.3);
        """)
        badge_row.addWidget(tag)
        badge_row.addStretch()
        header_lay.addLayout(badge_row)

        h1 = QLabel("Service Rules & Terms and Conditions")
        h1.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        header_lay.addWidget(h1)

        sub = QLabel("Please review and scroll through the catering service guidelines below before placing your order.")
        sub.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        header_lay.addWidget(sub)
        card_lay.addLayout(header_lay)

        # Scrollable Terms Content
        self._terms_view = QTextBrowser()
        self._terms_view.setFrameShape(QFrame.NoFrame)
        self._terms_view.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {theme.CARD_ELEVATED};
                border: 1.5px solid {theme.BORDER};
                border-radius: 12px;
                padding: 16px;
                color: #CBD5E1;
                font-size: 13.5px;
                line-height: 1.6;
            }}
        """)

        html_body = terms.TERMS_TEXT.strip().replace("\n\n", "</p><p>").replace("\n", "<br>")
        self._terms_view.setHtml(
            f"<div style='font-family:Segoe UI, sans-serif; color:#E2E8F0;'>"
            f"<h3 style='color:#F59E0B; margin-top:0;'>{terms.TERMS_TITLE}</h3>"
            f"<p>{html_body}</p>"
            f"<p style='color:{theme.TEXT_FAINT}; font-size:11px; margin-top:14px;'>Terms & Service Information Version {terms.CURRENT_TERMS_VERSION}</p>"
            f"</div>"
        )
        card_lay.addWidget(self._terms_view, 1)

        # Scroll helper hint
        self._hint_lbl = QLabel("Please scroll to the bottom of the terms agreement to enable acceptance.")
        self._hint_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #F59E0B;")
        card_lay.addWidget(self._hint_lbl)

        # Checkbox Agreement (Initially disabled until scrolled)
        self._ack_cb = QCheckBox(terms.TERMS_ACKNOWLEDGEMENT_LABEL)
        self._ack_cb.setEnabled(False)
        self._ack_cb.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                font-weight: 700;
                color: #FFFFFF;
                spacing: 12px;
                padding: 4px 0;
            }
            QCheckBox:disabled {
                color: #64748B;
            }
            QCheckBox::indicator {
                width: 24px;
                height: 24px;
                border-radius: 6px;
                border: 2px solid #F59E0B;
                background: #1A2438;
            }
            QCheckBox::indicator:disabled {
                border: 2px solid #334155;
                background: #0F172A;
            }
            QCheckBox::indicator:checked {
                background: #F59E0B;
                border: 2px solid #F59E0B;
            }
        """)
        self._ack_cb.setCursor(Qt.PointingHandCursor)
        card_lay.addWidget(self._ack_cb)

        # Connect scrollbar to check when bottom is reached
        vbar = self._terms_view.verticalScrollBar()
        vbar.valueChanged.connect(self._on_scroll)

        # Bottom Button Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        cancel_btn = QPushButton("  Cancel / Go Back")
        cancel_btn.setIcon(icons.icon_x("#94A3B8", 16))
        cancel_btn.setObjectName("Secondary")
        cancel_btn.setMinimumHeight(48)
        cancel_btn.setMinimumWidth(160)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        btn_row.addStretch()

        self._accept_btn = QPushButton("  I Agree & Start Order  >")
        self._accept_btn.setIcon(icons.icon_check("#FFFFFF", 16))
        self._accept_btn.setObjectName("Primary")
        self._accept_btn.setMinimumHeight(50)
        self._accept_btn.setMinimumWidth(240)
        self._accept_btn.setEnabled(False)
        self._accept_btn.setCursor(Qt.PointingHandCursor)
        self._accept_btn.setStyleSheet("""
            QPushButton#Primary {
                font-size: 15px;
                font-weight: 800;
                background-color: #D97706;
                color: #FFFFFF;
                border-radius: 10px;
                padding: 10px 24px;
            }
            QPushButton#Primary:hover {
                background-color: #B45309;
            }
            QPushButton#Primary:disabled {
                background-color: #334155;
                color: #64748B;
            }
        """)
        self._accept_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._accept_btn)

        self._ack_cb.toggled.connect(self._accept_btn.setEnabled)

        card_lay.addLayout(btn_row)
        backdrop.addWidget(card)

    def _on_scroll(self, value: int):
        if self._has_scrolled_to_bottom:
            return
        vbar = self._terms_view.verticalScrollBar()
        # Enable if at bottom (within 15px margin) or if no scrollbar is required
        if vbar.maximum() <= 0 or value >= vbar.maximum() - 15:
            self._unlock_checkbox()

    def _unlock_checkbox(self):
        self._has_scrolled_to_bottom = True
        self._ack_cb.setEnabled(True)
        self._hint_lbl.setText("You have reviewed the full agreement. Please check the box above to continue.")
        self._hint_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #10B981;")

    def _setup_animation(self):
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(220)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def showEvent(self, event):
        super().showEvent(event)
        self._anim.start()
        # Delayed check in case content fits completely without scrollbar
        QTimer.singleShot(150, self._check_initial_scroll)

    def _check_initial_scroll(self):
        if not self._has_scrolled_to_bottom:
            vbar = self._terms_view.verticalScrollBar()
            if vbar.maximum() <= 0:
                self._unlock_checkbox()
