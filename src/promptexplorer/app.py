import logging
import os
import sys
import tempfile
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QLibraryInfo, QSettings, QTimer, QTranslator
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from . import __version__
from .constants import APP_NAME, DB_FILENAME, ORG_NAME, THEME_ICON_PX
from .db import DB
from .paths import app_data_dir
from .ui.dialogs.startup_dialog import StartupDialog
from .ui.main_window import MainWindow
from .ui.utils import center_dialog, load_hidpi_icon, resource_path, theme_qss


def _close_smoke_window(app: QApplication, window: MainWindow) -> None:
    """Проверить настоящий диалог выхода в изолированном запуске сборки."""

    def confirm():
        dialog = app.activeModalWidget()
        if not isinstance(dialog, QMessageBox):
            app.exit(1)
            return
        dialog.button(QMessageBox.Yes).click()

    QTimer.singleShot(0, confirm)
    if not window.close():
        app.exit(1)


def main() -> int:
    """Запустить приложение, закрывая базу и журнал при любом способе выхода."""
    if "--version" in sys.argv:
        print(f"{APP_NAME} {__version__}")
        return 0
    if "--smoke-test" in sys.argv:
        # Автоматическая проверка не открывает окна поверх других приложений.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setFont(QFont("Segoe UI", 10))
    translator = QTranslator(app)
    if translator.load("qtbase_ru", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
    db = None
    smoke = "--smoke-test" in sys.argv
    temporary = tempfile.TemporaryDirectory(prefix="promptexplorer-smoke-") if smoke else None
    old_data_dir = os.environ.get("PROMPTEXPLORER_DATA_DIR")
    if temporary is not None:
        os.environ["PROMPTEXPLORER_DATA_DIR"] = temporary.name
    previous_hook = sys.excepthook
    try:
        data_dir = app_data_dir()
        handler = RotatingFileHandler(
            os.path.join(data_dir, "promptexplorer.log"),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger = logging.getLogger("promptexplorer")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        def report_error(exc_type, exc, traceback):
            logger.error("Не удалось выполнить действие", exc_info=(exc_type, exc, traceback))
            if smoke:
                app.exit(1)
                return
            QMessageBox.critical(
                app.activeWindow(),
                "Не удалось выполнить действие",
                f"{exc}\n\nПодробности записаны в журнал:\n{handler.baseFilename}",
            )

        sys.excepthook = report_error
        # В изолированном запуске настройки лежат рядом с явно выбранной базой.
        settings = (
            QSettings(os.path.join(data_dir, "settings.ini"), QSettings.IniFormat)
            if os.getenv("PROMPTEXPLORER_DATA_DIR")
            else QSettings(ORG_NAME, APP_NAME)
        )
        theme = settings.value("ui_theme", "light")
        if theme not in ("light", "dark"):
            theme = "light"
        icon = QIcon(resource_path("resources/app.ico"))
        app.setWindowIcon(icon)
        app.setStyleSheet(theme_qss(theme))
        db = DB(os.path.join(data_dir, DB_FILENAME))
        if db.last_migration_backup:
            logger.info("База обновлена; резервная копия: %s", db.last_migration_backup)
        startup = StartupDialog(db, icon, theme)
        center_dialog(startup)
        if smoke:
            profile = db.create_profile("Проверка сборки")
            db.upsert_prompt(
                profile, None, "Проверка", "Тестовый промт", "", "Свет", "Шум", "", "SDXL"
            )
            startup.reload_profiles()
            QTimer.singleShot(0, startup.on_continue)
        if startup.exec() != QDialog.Accepted or startup.selected_profile_id is None:
            return 1 if smoke else 0
        window = MainWindow(
            db,
            icon,
            load_hidpi_icon("resources/moon.png", THEME_ICON_PX),
            load_hidpi_icon("resources/sun.png", THEME_ICON_PX),
            startup.selected_profile_id,
            settings,
            theme,
        )
        window.show()
        if smoke:
            window.search.setText("тестовый")
            window.refresh_list()
            if window.list.count() != 1 or icon.isNull():
                raise RuntimeError("Проверка сборки: промт или ресурсы недоступны.")
            window.toggle_theme()
            QTimer.singleShot(350, lambda: _close_smoke_window(app, window))
        return app.exec()
    except Exception:
        if sys.excepthook is not previous_hook:
            sys.excepthook(*sys.exc_info())
        else:
            QMessageBox.critical(None, "Ошибка запуска", str(sys.exc_info()[1]))
        return 1
    finally:
        sys.excepthook = previous_hook
        if db is not None:
            db.close()
        if "handler" in locals():
            logger.removeHandler(handler)
            handler.close()
        if temporary is not None:
            if old_data_dir is None:
                os.environ.pop("PROMPTEXPLORER_DATA_DIR", None)
            else:
                os.environ["PROMPTEXPLORER_DATA_DIR"] = old_data_dir
            temporary.cleanup()
