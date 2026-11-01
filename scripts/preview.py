"""Создать снимки интерфейса на демонстрационных данных без пользовательской базы."""

import argparse
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QLibraryInfo, QSettings, QTimer, QTranslator
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import QApplication, QMessageBox

from promptexplorer.db import DB
from promptexplorer.ui.dialogs.prompt_dialog import PromptDialog
from promptexplorer.ui.dialogs.startup_dialog import StartupDialog
from promptexplorer.ui.image_preview import thumbnail_from_file
from promptexplorer.ui.main_window import MainWindow
from promptexplorer.ui.utils import load_hidpi_icon, resource_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Папка для снимков")
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    translator = QTranslator(app)
    if translator.load("qtbase_ru", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
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
            # Демонстрационный ночной пейзаж, не пользовательская картинка.
            art = QImage(512, 640, QImage.Format_RGB32)
            painter = QPainter(art)
            sky = QLinearGradient(0, 0, 0, 640)
            sky.setColorAt(0, QColor("#101c38"))
            sky.setColorAt(1, QColor("#6c5080"))
            painter.fillRect(art.rect(), sky)
            painter.setPen(QColor("#f2e4c9"))
            painter.setBrush(QColor("#f2e4c9"))
            painter.drawEllipse(330, 80, 85, 85)
            painter.setPen(QColor("#152037"))
            painter.setBrush(QColor("#152037"))
            for x, y, width in [
                (0, 390, 90),
                (70, 320, 100),
                (160, 370, 110),
                (260, 290, 90),
                (340, 350, 100),
                (430, 310, 90),
            ]:
                painter.drawRect(x, y, width, 640 - y)
                for wx in range(x + 16, x + width - 10, 24):
                    for wy in range(y + 24, 620, 40):
                        painter.fillRect(wx, wy, 7, 12, QColor("#d8ad83"))
            painter.end()
            art_path = Path(folder) / "example.png"
            art.save(str(art_path))
            selected = next(p.id for p in db.list_prompts(profile) if p.name == "Ночной город")
            db.upsert_prompt(
                profile,
                selected,
                "Пейзажи",
                "Ночной город",
                "Мягкий свет, отражения на мокром асфальте и спокойная ночная атмосфера.",
                "cinematic cityscape, rain-soaked avenue, warm window light, deep blue sky, "
                "quiet streets, subtle reflections, architectural photography, soft shadows, "
                "atmospheric perspective, detailed facades, balanced composition, film grain",
                "blurry, low quality, harsh contrast, oversaturated colors, artifacts",
                "architectural-detail:0.6\nnight-lighting:0.4",
                "SDXL 1.0",
                metadata={
                    "workflow": "img2img:hires-fix",
                    "priority": "low",
                    "output_format": "JPEG",
                    "sampler": "Euler A",
                    "cfg_scale": "4",
                    "steps": "40",
                    "clip_skip": "2",
                    "seed": "147572794",
                    "denoise": "0.5",
                    "quantity": "1",
                },
            )
            window.select_prompt(selected)
            window.save_preview(thumbnail_from_file(str(art_path)))
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-light.png"))
            window.toggle_theme()
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-dark.png"))
            window.detail.verticalScrollBar().setValue(window.detail.verticalScrollBar().maximum())
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-metadata.png"))
            window.detail.verticalScrollBar().setValue(0)
            square = art.copy(0, 64, 512, 512)
            square_path = Path(folder) / "square.png"
            square.save(str(square_path))
            window.save_preview(thumbnail_from_file(str(square_path)))
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-square.png"))
            landscape = art.copy(0, 200, 512, 256)
            landscape_path = Path(folder) / "landscape.png"
            landscape.save(str(landscape_path))
            window.save_preview(thumbnail_from_file(str(landscape_path)))
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-landscape.png"))
            window.save_preview(thumbnail_from_file(str(art_path)))
            window.tabs.setCurrentIndex(1)
            app.processEvents()
            window.grab().save(str(output / "PromptExplorer-stats.png"))
            dialog = PromptDialog(
                ["Пейзажи", "Портреты"], icon, "dark", db.get_prompt(selected, profile)
            )
            dialog.resize(700, 680)
            dialog.show()
            app.processEvents()
            dialog.grab().save(str(output / "PromptExplorer-editor.png"))
            from PySide6.QtWidgets import QScrollArea

            fields_scroll = dialog.findChild(QScrollArea)
            fields_scroll.verticalScrollBar().setValue(fields_scroll.verticalScrollBar().maximum())
            app.processEvents()
            dialog.grab().save(str(output / "PromptExplorer-metadata-editor.png"))
            dialog.close()
            startup = StartupDialog(db, icon, "light")
            startup.show()
            app.processEvents()
            startup.grab().save(str(output / "PromptExplorer-profiles.png"))
            startup.close()

            def capture_exit_confirmation():
                """Снять настоящий диалог и отменить закрытие демонстрационного окна."""
                question = app.activeModalWidget()
                question.grab().save(str(output / "PromptExplorer-exit.png"))
                question.button(QMessageBox.No).click()

            QTimer.singleShot(0, capture_exit_confirmation)
            window.close()
            window.hide()
            window.deleteLater()
            app.processEvents()
        finally:
            db.close()


if __name__ == "__main__":
    main()
