from PySide6.QtWidgets import QMainWindow, QStackedWidget

from ui.home_view import HomeView
from ui.order_wizard import OrderWizard
from version import get_version_string


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(get_version_string())
        self.resize(1100, 800)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._home = HomeView(on_new_order=self._start_new_order)
        self._stack.addWidget(self._home)
        self._stack.setCurrentWidget(self._home)

        self._wizard = None

    def _start_new_order(self):
        self._wizard = OrderWizard(on_finish=self._finish_wizard)
        self._stack.addWidget(self._wizard)
        self._stack.setCurrentWidget(self._wizard)

    def _finish_wizard(self):
        self._stack.setCurrentWidget(self._home)
        self._home.reload()
        if self._wizard is not None:
            self._stack.removeWidget(self._wizard)
            self._wizard.deleteLater()
            self._wizard = None
