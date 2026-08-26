from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

from ui.home_view import HomeView
from ui.order_wizard import OrderWizard
from version import get_version_string


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(get_version_string())
        self.resize(1180, 820)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._home = HomeView(on_new_order=self._start_new_order, on_toggle_fullscreen=self.toggle_fullscreen)
        self._stack.addWidget(self._home)
        self._stack.setCurrentWidget(self._home)

        self._wizard = None

        # F11 Shortcut for Fullscreen Toggle
        self._f11_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        self._f11_shortcut.activated.connect(self.toggle_fullscreen)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _start_new_order(self):
        self._wizard = OrderWizard(on_finish=self._finish_wizard, on_toggle_fullscreen=self.toggle_fullscreen)
        self._stack.addWidget(self._wizard)
        self._stack.setCurrentWidget(self._wizard)

    def _finish_wizard(self):
        self._stack.setCurrentWidget(self._home)
        self._home.reload()
        if self._wizard is not None:
            self._stack.removeWidget(self._wizard)
            self._wizard.deleteLater()
            self._wizard = None

