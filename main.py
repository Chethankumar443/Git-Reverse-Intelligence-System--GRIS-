import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.views.main_window import MainWindow


from PySide6.QtGui import QIcon

def main():
    """Main Application Entrypoint for Git Reverse Desktop."""
    app = QApplication(sys.argv)
    app.setApplicationName("Git Reverse")
    app.setOrganizationName("GitReverse")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".agents", "skills", "favicon (1)", "favicon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
