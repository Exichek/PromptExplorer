"""Создать снимки интерфейса на демонстрационных данных без пользовательской базы."""

import argparse
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from promptexplorer.db import DB
from promptexplorer.ui.dialogs.prompt_dialog import PromptDialog
from promptexplorer.ui.dialogs.startup_dialog import StartupDialog
from promptexplorer.ui.main_window import MainWindow
from promptexplorer.ui.utils import load_hidpi_icon, resource_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Папка для снимков")
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    if os.name == "nt":
        # Платформа offscreen не обнаруживает системные шрифты Windows сама.
        QFontDatabase.addApplicationFont(
            str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf")
        )
    app.setFont(QFont("Segoe UI", 10))
    with tempfile.TemporaryDirectory() as folder:
        os.environ["PROMPTEXPLORER_DATA_DIR"] = folder
        db = DB(str(Path(folder) / "preview.sqlite3"))
        try:
            profile = db.create_profile("Основная коллекция")
            for category, name in [
                ("Пейзажи", "Туманный лес"),
                ("Пейзажи", "Ночной город"),
                ("Портреты", "Студийный портрет"),
                ("Предметы", "Керамика"),
            ]:
                db.upsert_prompt(
                    profile,
                    None,
                    category,
                    name,
                    "Мягкое освещение, спокойная композиция. Вариант для дальнейших экспериментов.",
                    "cinematic lighting, detailed textures, soft shadows, atmospheric composition",
                    "blurry, low quality, artifacts",
                    "detail-enhancer:0.6",
                    "SDXL",
                )
            icon = QIcon(resource_path("resources/app.ico"))
            settings = QSettings(str(Path(folder) / "settings.ini"), QSettings.IniFormat)
            window = MainWindow(
                db,
                icon,
                load_hidpi_icon("resources/moon.png", 44),
                load_hidpi_icon("resources/sun.png", 44),
                profile,
                settings,
                "light",
            )
            window.resize(1320, 800)
            window.show()
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-light.png"))
            window.toggle_theme()
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-dark.png"))
            window.tabs.setCurrentIndex(1)
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-stats.png"))
            dialog = PromptDialog(
                ["Пейзажи", "Портреты"], icon, "dark", db.list_prompts(profile)[0]
            )
            dialog.resize(700, 680)
            dialog.show()
            app.processEvents()
            dialog.grab().save(str(output / "PromptExplorer-editor.png"))
            dialog.close()
            startup = StartupDialog(db, icon, "light")
            startup.show()
            app.processEvents()
            startup.grab().save(str(output / "PromptExplorer-profiles.png"))
            startup.close()
            window.close()
        finally:
            db.close()


if __name__ == "__main__":
    main()
