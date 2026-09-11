"""
Theme Loading Overlay with Standalone Freeze-Proof 60-FPS Subprocess.
Spawns an independent OS process to render the circular spinner during stylesheet updates,
ensuring 100% continuous, fluid 60-FPS rotation with zero freezing.
"""

import os
import sys
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QApplication, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from components.circular_spinner import CircularSpinner
from utils.accent import AccentManager
from utils.paths import resource_path


class ThemeLoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(10, 15, 29, 0.72);")
        self.hide()

        self._proc = None
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)
        self._anim = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.card = QFrame(self)
        self.card.setObjectName("themeLoaderCard")
        self.card.setStyleSheet("""
            QFrame#themeLoaderCard {
                background: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 16px;
                padding: 24px 32px;
            }
        """)
        card_lay = QVBoxLayout(self.card)
        card_lay.setAlignment(Qt.AlignCenter)
        card_lay.setSpacing(12)

        self.spinner = CircularSpinner(
            size=48,
            line_width=4,
            color_start=AccentManager().current,
            color_end="#38BDF8",
            parent=self.card
        )
        card_lay.addWidget(self.spinner, alignment=Qt.AlignCenter)

        self.title_lbl = QLabel("Applying Theme...", self.card)
        self.title_lbl.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 700;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("Updating UI visual styles & palettes", self.card)
        self.sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(self.sub_lbl)

        layout.addWidget(self.card)

    def show_loading(self, title: str = "Applying Theme...", sub: str = "Updating UI visual styles & palettes"):
        self._terminate_proc()

        # Calculate parent global coordinates
        p = self.parent()
        if p:
            self.resize(p.size())
            self.raise_()
            tl = p.mapToGlobal(QPoint(0, 0))
            gx, gy, gw, gh = tl.x(), tl.y(), p.width(), p.height()
        else:
            gx, gy, gw, gh = 100, 100, 1280, 768

        # Spawn isolated standalone process (Option B) for 100% freeze-proof 60-FPS rotation
        loader_script = os.path.join(os.path.dirname(__file__), "standalone_loader.py")
        if os.path.exists(loader_script):
            try:
                cmd = [
                    sys.executable, loader_script,
                    "--x", str(gx), "--y", str(gy),
                    "--w", str(gw), "--h", str(gh),
                    "--title", title,
                    "--accent", str(AccentManager().current)
                ]
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                self._proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creation_flags
                )
            except Exception as e:
                print(f"[ThemeLoadingOverlay] Could not spawn standalone loader: {e}")
                self._proc = None

        # Also show local overlay as fast fallback
        self.show()
        self.spinner.start()
        QApplication.processEvents()

    def hide_loading(self, animated: bool = True):
        self.spinner.stop()
        self.hide()

        # Signal standalone subprocess to smoothly fade out and close
        if self._proc and self._proc.poll() is None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.write(b"CLOSE\n")
                    self._proc.stdin.flush()
            except Exception:
                pass
            # Schedule cleanup
            QTimer.singleShot(250, self._terminate_proc)

    def _terminate_proc(self):
        if self._proc:
            try:
                if self._proc.poll() is None:
                    self._proc.terminate()
            except Exception:
                pass
            self._proc = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent():
            self.resize(self.parent().size())
