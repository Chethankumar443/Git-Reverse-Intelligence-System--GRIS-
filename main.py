import sys
import os
import argparse

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app._version import __version__, __app_name__
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon


def parse_args():
    parser = argparse.ArgumentParser(
        prog="gitreverse",
        description="Git Reverse Intelligence System (GRIS) — Production Repository Intelligence Desktop Platform",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"{__app_name__} v{__version__}"
    )
    parser.add_argument(
        "--reset-setup",
        action="store_true",
        help="Reset first-run onboarding wizard preferences",
    )
    return parser.parse_args()


def main():
    """Main Application Entrypoint for Git Reverse Desktop."""
    args = parse_args()

    if args.reset_setup:
        from app.services.secrets import SecretsManager
        config = SecretsManager.load_config()
        config["first_run_complete"] = False
        SecretsManager.save_config(config)
        print("First-run onboarding wizard state reset successfully.")

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setOrganizationName("GitReverse")

    icon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        ".agents",
        "skills",
        "favicon (1)",
        "favicon.ico",
    )
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from app.views.main_window import MainWindow

    window = MainWindow()
    window.show()

    def cleanup():
        # Stop active worker threads on exit to prevent QThread destruction warnings
        for worker in getattr(window, "_active_workers", []):
            if worker and worker.isRunning():
                worker.quit()
                worker.wait(500)

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
