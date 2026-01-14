from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QToolTip,
    QVBoxLayout,
    QInputDialog,
)

from ..db import DB
from ..utils import theme_qss


# ============================================================
# Dialog: Startup profile selection (create / import / delete)
# ============================================================

class StartupDialog(QDialog):

    def __init__(self, db: DB, icon: QIcon, theme: str):
        super().__init__()
        self.db = db
        self.selected_profile_id: int | None = None

        self.setWindowTitle("Выбор профиля")
        self.setWindowIcon(icon)
        self.setStyleSheet(theme_qss(theme))

        self.copy_path_text = r"%APPDATA%/PromptExplorer"
        self.info = QLabel(
            'Выбери профиль или создай/импортируй. Профили хранятся в папке: '
            f'<a href="copy_path">{self.copy_path_text}</a>')
        self.info.setObjectName("Hint")
        self.info.setTextFormat(Qt.RichText)
        self.info.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.info.setOpenExternalLinks(False)
        self.info.linkActivated.connect(self.on_info_link)

        self.profile_combo = QComboBox()

        self.btn_continue = QPushButton("Продолжить")
        self.btn_new = QPushButton("Создать новый профиль")
        self.btn_import = QPushButton("Импорт профиля (из БД)")
        self.btn_delete = QPushButton("Удалить профиль")

        self.btn_continue.clicked.connect(self.on_continue)
        self.btn_new.clicked.connect(self.on_new)
        self.btn_import.clicked.connect(self.on_import)
        self.btn_delete.clicked.connect(self.on_delete)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.profile_combo)
        row = QHBoxLayout()
        row.addWidget(self.btn_new)
        row.addWidget(self.btn_import)
        row.addWidget(self.btn_delete)
        row.addStretch(1)
        row.addWidget(self.btn_continue)
        layout.addLayout(row)

        self.setMinimumWidth(780)

        self.reload_profiles()

        self.btn_delete.setEnabled(self.profile_combo.currentData() is not None)
        self.profile_combo.currentIndexChanged.connect(
            lambda: self.btn_delete.setEnabled(self.profile_combo.currentData() is not None)
        )

    def on_info_link(self, link: str) -> None:
        if link != "copy_path":
            return

        QApplication.clipboard().setText(self.copy_path_text)
        QToolTip.showText(QCursor.pos(), "Скопировано!")

    def reload_profiles(self) -> None:
        self.profile_combo.clear()
        profiles = self.db.list_profiles()

        if not profiles:
            self.profile_combo.setEnabled(False)
            self.btn_continue.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.profile_combo.addItem("Профилей нет — создай или импортируй", None)
            return

        self.profile_combo.setEnabled(True)
        self.btn_continue.setEnabled(True)

        for pid, name, _theme in profiles:
            self.profile_combo.addItem(name, pid)

    def on_continue(self) -> None:
        pid = self.profile_combo.currentData()
        if pid is None:
            return
        self.selected_profile_id = int(pid)
        self.accept()

    def on_new(self) -> None:
        name, ok = QInputDialog.getText(self, "Новый профиль", "Имя профиля:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return

        pid = self.db.create_profile(name, "light")
        self.reload_profiles()

        idx = self.profile_combo.findData(pid)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

    def on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать БД профиля",
            "",
            "SQLite DB (*.sqlite3 *.db);;All files (*.*)",
        )
        if not path:
            return

        try:
            profiles = DB.read_profiles_from_db(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка!", f"Некорректный файл базы данных.\n\n{e}")
            return

        if not profiles:
            QMessageBox.warning(self, "Пусто", "В выбранной базе нет профилей.")
            return

        items = [f"{pid}: {name} ({theme})" for pid, name, theme in profiles]
        choice, ok = QInputDialog.getItem(self, "Импорт профиля", "Выбери профиль:", items, 0, False)
        if not ok or not choice:
            return

        ext_pid = int(choice.split(":")[0])

        try:
            new_pid = self.db.import_profile_from_db(path, ext_pid)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка!", f"Не смог импортировать профиль.\n\n{e}")
            return

        self.reload_profiles()
        idx = self.profile_combo.findData(new_pid)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

    def on_delete(self) -> None:

        pid = self.profile_combo.currentData()
        if pid is None:
            return
        pid = int(pid)

        name = self.profile_combo.currentText()

        r = QMessageBox.question(
            self,
            "Удалить профиль",
            f"Удалить профиль «{name}»?\n\nБудут удалены ВСЕ типы и промты этого профиля.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return

        try:
            self.db.delete_profile(pid)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка!", f"Не смог удалить профиль.\n\n{e}")
            return

        self.reload_profiles()
