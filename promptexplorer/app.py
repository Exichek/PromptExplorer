# ============================================================
# PromptExplorer — version 0.9.0.0 beta
# ============================================================

import os
import sys

from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialog

from .constants import APP_NAME, ORG_NAME, THEME_ICON_PX, DB_FILENAME
from .db import DB
from .dialogs.startup_dialog import StartupDialog
from .main_window import MainWindow
from .utils import app_data_dir, center_dialog, load_hidpi_icon, resource_path, theme_qss


# ============================================================
# Entry point
# ============================================================

def main() -> None:
    # QApplication
    app = QApplication(sys.argv)

    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)

    app.setFont(QFont("Segoe UI", 10))

    settings = QSettings(ORG_NAME, APP_NAME)
    saved_theme = settings.value("ui_theme", "light")
    if saved_theme not in ("light", "dark"):
        saved_theme = "light"

    app_icon = QIcon(resource_path("resources/app.ico"))
    app.setWindowIcon(app_icon)

    moon_icon = load_hidpi_icon("resources/moon.png", THEME_ICON_PX)
    sun_icon = load_hidpi_icon("resources/sun.png", THEME_ICON_PX)

    app.setStyleSheet(theme_qss(saved_theme))

    # %APPDATA%/PromptExplorer
    db_path = os.path.join(app_data_dir(), DB_FILENAME)
    db = DB(db_path)

    sd = StartupDialog(db, app_icon, saved_theme)
    center_dialog(sd)

    if sd.exec() != QDialog.Accepted:
        return

    profile_id = sd.selected_profile_id
    if profile_id is None:
        return

    # --- Main window ---
    w = MainWindow(db, app_icon, moon_icon, sun_icon, profile_id, settings, saved_theme)
    w.show()

    # main Qt cycle
    sys.exit(app.exec())
