import logging
from datetime import datetime

from PySide6.QtCore import QPoint, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..constants import APP_NAME, THEME_BTN_SIZE, THEME_ICON_PX
from ..db import DB
from ..models import Prompt
from ..paths import now_iso
from .dialogs.prompt_dialog import PromptDialog
from .image_preview import ImagePreview
from .utils import center_dialog, theme_qss


class MainWindow(QMainWindow):
    """Коллекция промтов, поиск, статистика и резервное копирование."""

    def __init__(
        self,
        db: DB,
        icon: QIcon,
        moon_icon: QIcon | None,
        sun_icon: QIcon | None,
        profile_id: int,
        settings: QSettings,
        theme: str,
    ):
        super().__init__()

        self.db = db
        self.icon = icon
        self.moon_icon = moon_icon
        self.sun_icon = sun_icon
        self.settings = settings

        self.profile_id = int(profile_id)
        self.theme = theme if theme in ("light", "dark") else "light"

        self.apply_theme()

        prof = self.db.get_profile(self.profile_id)
        self.profile_name = prof["name"] if prof else "Неизвестный профиль"
        self.setWindowTitle(f"{APP_NAME} — {self.profile_name}")
        self.setWindowIcon(icon)

        self.resize(1200, 720)

        self._build_toolbar()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_prompts_tab()
        self._build_stats_tab()

        self.refresh_all()
        geometry = self.settings.value("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        splitter_state = self.settings.value("splitter_state")
        if splitter_state:
            self.splitter.restoreState(splitter_state)
        for sequence, callback in (
            ("Ctrl+F", self.search.setFocus),
            ("Ctrl+N", self.create_prompt),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Закрыть программу только после подтверждения пользователя."""
        answer = QMessageBox.question(
            self,
            "Закрыть программу?",
            "Вы точно хотите закрыть PromptExplorer?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            event.ignore()
            return
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("splitter_state", self.splitter.saveState())
        event.accept()

    def apply_theme(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.instance().setStyleSheet(theme_qss(self.theme))

    def update_theme_button(self) -> None:
        if self.theme == "light":
            if self.moon_icon and not self.moon_icon.isNull():
                self.theme_btn.setIcon(self.moon_icon)
                self.theme_btn.setText("")
            else:
                self.theme_btn.setIcon(QIcon())
                self.theme_btn.setText("Т")
        else:
            if self.sun_icon and not self.sun_icon.isNull():
                self.theme_btn.setIcon(self.sun_icon)
                self.theme_btn.setText("")
            else:
                self.theme_btn.setIcon(QIcon())
                self.theme_btn.setText("С")

        self.theme_btn.setIconSize(QSize(THEME_ICON_PX, THEME_ICON_PX))
        self.theme_btn.setFixedSize(THEME_BTN_SIZE, THEME_BTN_SIZE)

    def toggle_theme(self) -> None:
        self.theme = "dark" if self.theme == "light" else "light"
        self.settings.setValue("ui_theme", self.theme)
        self.apply_theme()
        self.update_theme_button()

    def _build_toolbar(self) -> None:
        tb = QToolBar()
        tb.setMovable(False)

        tb.setMinimumHeight(THEME_BTN_SIZE + 10)
        self.addToolBar(Qt.TopToolBarArea, tb)

        tb.addWidget(QLabel("Профиль: "))

        self.profile_combo = QComboBox()
        tb.addWidget(self.profile_combo)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        backup_button = QPushButton("Резервная копия")
        backup_button.clicked.connect(self.backup_database)
        tb.addWidget(backup_button)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("ThemeBtn")
        self.theme_btn.setToolTip("Переключить тему")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.theme_btn.setCursor(Qt.PointingHandCursor)

        tb.addWidget(self.theme_btn)

        self.reload_profiles_into_combo()
        self.update_theme_button()

    def reload_profiles_into_combo(self) -> None:
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()

        for pid, name, _ in self.db.list_profiles():
            self.profile_combo.addItem(name, pid)

        idx = self.profile_combo.findData(self.profile_id)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

        self.profile_combo.blockSignals(False)

    def on_profile_changed(self) -> None:
        pid = self.profile_combo.currentData()
        if pid is None:
            return

        self.profile_id = int(pid)
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.tree.blockSignals(True)
        self.tree.clear()
        self.tree.blockSignals(False)
        self.list.clear()

        prof = self.db.get_profile(self.profile_id)
        self.profile_name = prof["name"] if prof else "Неизвестный профиль"
        self.setWindowTitle(f"{APP_NAME} — {self.profile_name}")

        self.refresh_all()

    def _wrap_card(self, w: QWidget) -> QWidget:
        card = QWidget()
        card.setObjectName("Card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(w)

        return card

    def _build_prompts_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)

        splitter = QSplitter(Qt.Horizontal)
        self.splitter = splitter

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_add_type = QPushButton("+ Категория")
        self.btn_add_type.clicked.connect(self.add_type)

        self.tree = QTreeWidget()
        self.tree.setMinimumWidth(170)
        self.tree.setIndentation(0)
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self.on_type_changed)

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_type_context_menu)

        left_layout.addWidget(self.btn_add_type)
        left_layout.addWidget(self.tree)

        middle = QWidget()
        middle.setMinimumWidth(280)
        middle_layout = QVBoxLayout(middle)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по коллекции · Ctrl+F")
        self.search.setToolTip("Название, категория, описание, Positive, Negative, LoRA и модель")
        self.search.setClearButtonEnabled(True)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search.textChanged.connect(lambda: self.search_timer.start())
        self.search_timer.timeout.connect(self.refresh_list)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.on_prompt_selected)
        self.list.itemDoubleClicked.connect(lambda: self.edit_prompt())
        middle_layout.addWidget(self.search)
        middle_layout.addWidget(self.list)

        right = QWidget()
        r = QVBoxLayout(right)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        btn_row = QHBoxLayout()
        self.btn_new = QPushButton("Создать")
        self.btn_edit = QPushButton("Редактировать")
        self.btn_del = QPushButton("Удалить")
        self.btn_export = QPushButton("Выгрузить .txt")

        self.btn_new.clicked.connect(self.create_prompt)
        self.btn_edit.clicked.connect(self.edit_prompt)
        self.btn_del.clicked.connect(self.delete_prompt)
        self.btn_export.clicked.connect(self.export_prompts)

        for b in (self.btn_new, self.btn_edit, self.btn_del, self.btn_export):
            btn_row.addWidget(b)
        btn_row.addStretch(1)

        r.addLayout(btn_row)
        copy_row = QHBoxLayout()
        self.copy_positive = QPushButton("Копировать Positive")
        self.copy_negative = QPushButton("Копировать Negative")
        self.copy_positive.clicked.connect(lambda: self.copy_prompt_field("positive"))
        self.copy_negative.clicked.connect(lambda: self.copy_prompt_field("negative"))
        copy_row.addWidget(self.copy_positive)
        copy_row.addWidget(self.copy_negative)
        copy_row.addStretch()
        r.addLayout(copy_row)
        details = QHBoxLayout()
        self.preview = ImagePreview()
        self.preview.image_selected.connect(self.save_preview)
        self.preview.remove_requested.connect(lambda: self.save_preview(None))
        details.addWidget(self.detail, 1)
        details.addWidget(self.preview)
        r.addLayout(details, 1)

        splitter.addWidget(self._wrap_card(left_col))
        splitter.addWidget(self._wrap_card(middle))
        splitter.addWidget(self._wrap_card(right))

        splitter.setSizes([210, 320, 670])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 1)

        layout.addWidget(splitter)
        self.tabs.addTab(page, "Промты")

    def _build_stats_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.stats_label = QLabel("")
        self.stats_label.setObjectName("Hint")
        self.stats_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.stats_list = QListWidget()

        layout.addWidget(self._wrap_card(self.stats_label))
        layout.addWidget(self._wrap_card(self.stats_list))

        self.tabs.addTab(page, "Статистика")

    def refresh_types(self) -> None:
        selected_type = self.current_type_id()
        self.tree.blockSignals(True)
        self.tree.clear()

        all_item = QTreeWidgetItem(["Все категории"])
        all_item.setData(0, Qt.UserRole, None)
        self.tree.addTopLevelItem(all_item)
        selected_item = all_item

        for tid, name in self.db.list_types(self.profile_id):
            it = QTreeWidgetItem([name])
            it.setData(0, Qt.UserRole, tid)
            self.tree.addTopLevelItem(it)
            if tid == selected_type:
                selected_item = it

        self.tree.expandAll()
        self.tree.setCurrentItem(selected_item)
        self.tree.blockSignals(False)

    def current_type_id(self) -> int | None:
        it = self.tree.currentItem()
        if not it:
            return None
        return it.data(0, Qt.UserRole)

    def add_type(self) -> None:
        name, ok = QInputDialog.getText(self, "Новый тип", "Название типа:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return

        try:
            self.db.create_type_if_missing(self.profile_id, name)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка!", f"Не смог создать тип:\n{e}")
            return

        self.refresh_types()

        items = self.tree.findItems(name, Qt.MatchExactly | Qt.MatchRecursive, 0)
        if items:
            self.tree.setCurrentItem(items[0])

    def on_type_context_menu(self, pos: QPoint) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return

        type_id = item.data(0, Qt.UserRole)
        if type_id is None:
            return

        menu = QMenu(self)
        act_rename = menu.addAction("Переименовать")
        act_delete = menu.addAction("Удалить")

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == act_rename:
            self.rename_type(int(type_id))
        elif action == act_delete:
            self.delete_type(int(type_id))

    def rename_type(self, type_id: int) -> None:
        old_name = self.db.get_type_name(self.profile_id, type_id)
        new_name, ok = QInputDialog.getText(self, "Переименовать тип", "Новое имя:", text=old_name)
        if not ok:
            return
        new_name = (new_name or "").strip()
        if not new_name:
            return

        try:
            self.db.rename_type(self.profile_id, type_id, new_name)
        except ValueError:
            QMessageBox.warning(self, "Ошибка!", "Такое имя уже есть.")
            return
        except Exception as e:
            QMessageBox.warning(self, "Ошибка!", str(e))
            return

        self.refresh_all()

    def delete_type(self, type_id: int) -> None:
        name = self.db.get_type_name(self.profile_id, type_id)
        cnt = self.db.type_prompt_count(self.profile_id, type_id)

        if cnt > 0:
            r = QMessageBox.question(
                self,
                "Удалить тип",
                f"Тип «{name}» содержит промты: {cnt}.\n\nУдалить тип и ВСЕ промты внутри?",
                QMessageBox.Yes | QMessageBox.No,
            )
        else:
            r = QMessageBox.question(
                self,
                "Удалить тип",
                f"Удалить тип «{name}»?",
                QMessageBox.Yes | QMessageBox.No,
            )

        if r != QMessageBox.Yes:
            return

        self.db.delete_type_and_prompts(self.profile_id, type_id)
        self.refresh_all()

    def refresh_list(self) -> None:
        selected_id = self.selected_prompt_id()
        self.list.blockSignals(True)
        self.list.clear()

        type_id = self.current_type_id()
        prompts = self.db.list_prompts(self.profile_id, type_id, self.search.text())

        for p in prompts:
            it = QListWidgetItem(f"[{p.type}] {p.name}")
            it.setData(Qt.UserRole, p.id)
            self.list.addItem(it)
            if p.id == selected_id:
                self.list.setCurrentItem(it)

        if self.list.currentItem() is None and self.list.count() > 0:
            self.list.setCurrentRow(0)
        self.list.blockSignals(False)
        self.on_prompt_selected(self.list.currentItem(), None)
        self.statusBar().showMessage(f"Найдено промтов: {len(prompts)}")

    def refresh_stats(self) -> None:
        total = self.db.stats_total(self.profile_id)
        self.stats_label.setText(
            f"Профиль: {self.profile_name}\nВсего промтов: {total}\nКатегорий: {len(self.db.list_types(self.profile_id))}"
        )

        self.stats_list.clear()
        for row in self.db.stats_by_type(self.profile_id):
            self.stats_list.addItem(f"{row['name']} — {row['count']}")

    def refresh_all(self) -> None:
        self.refresh_types()
        self.refresh_list()
        self.refresh_stats()

    def on_type_changed(self) -> None:
        self.refresh_list()

    def on_prompt_selected(self, current: QListWidgetItem, prev: QListWidgetItem) -> None:
        for button in (self.btn_edit, self.btn_del, self.copy_positive, self.copy_negative):
            button.setEnabled(current is not None)
        if not current:
            self.preview.set_image(None, enabled=False)
            self.detail.setPlainText(
                "Ничего не найдено." if self.search.text() else "Создайте промт."
            )
            return
        pid = int(current.data(Qt.UserRole))
        p = self.db.get_prompt(pid, self.profile_id)
        self.detail.setPlainText(self.render_prompt_text(p) if p else "Промт не найден.")
        self.preview.set_image(p.preview if p else None, enabled=p is not None)

    def save_preview(self, data: bytes | None) -> None:
        """Сохранить картинку выбранного промта и обновить миниатюру после успеха."""
        pid = self.selected_prompt_id()
        if pid is None:
            return
        try:
            self.db.set_prompt_preview(self.profile_id, pid, data)
        except Exception as exc:
            logging.getLogger(__name__).exception("Не удалось сохранить превью")
            QMessageBox.critical(self, "Ошибка сохранения превью", str(exc))
            return
        self.preview.set_image(data)
        self.statusBar().showMessage("Превью сохранено" if data else "Превью удалено", 2500)

    def selected_prompt_id(self) -> int | None:
        item = self.list.currentItem()
        return int(item.data(Qt.UserRole)) if item else None

    def select_prompt(self, prompt_id: int) -> None:
        """Показать сохранённый промт, сохраняя фильтры, пока он в них виден."""
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.data(Qt.UserRole) == prompt_id:
                self.list.setCurrentItem(item)
                return
        prompt = self.db.get_prompt(prompt_id, self.profile_id)
        if prompt is None:
            return
        self.search.clear()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item.data(0, Qt.UserRole) is not None and item.text(0) == prompt.type:
                self.tree.setCurrentItem(item)
                break
        self.refresh_list()
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.data(Qt.UserRole) == prompt_id:
                self.list.setCurrentItem(item)
                return

    def copy_prompt_field(self, field: str) -> None:
        """Скопировать выбранную часть промта без заголовков и служебного текста."""
        prompt = self.db.get_prompt(self.selected_prompt_id(), self.profile_id)
        if prompt is not None:
            QApplication.clipboard().setText(getattr(prompt, field))
            self.statusBar().showMessage("Скопировано в буфер обмена", 2500)

    def backup_database(self) -> None:
        """Сохранить согласованную копию всех профилей через SQLite Backup API."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Резервная копия всех профилей",
            f"PromptExplorer-{stamp}.sqlite3",
            "SQLite (*.sqlite3)",
        )
        if not path:
            return
        try:
            self.db.backup_to(path)
            QMessageBox.information(self, "Готово", f"Резервная копия сохранена:\n{path}")
        except Exception as exc:
            logging.getLogger(__name__).exception("Не удалось создать резервную копию")
            QMessageBox.critical(self, "Ошибка резервного копирования", str(exc))

    def create_prompt(self) -> None:
        types = [name for _, name in self.db.list_types(self.profile_id)]
        dlg = PromptDialog(types, self.icon, self.theme, existing=None)
        center_dialog(dlg, self)

        if dlg.exec() != QDialog.Accepted:
            return

        while True:
            try:
                pid = self.db.upsert_prompt(self.profile_id, None, **dlg.data())
                break
            except Exception as exc:
                logging.getLogger(__name__).exception("Не удалось создать промт")
                QMessageBox.critical(self, "Ошибка сохранения", str(exc))
                if dlg.exec() != QDialog.Accepted:
                    return
        self.refresh_all()
        self.select_prompt(pid)

    def edit_prompt(self) -> None:
        pid = self.selected_prompt_id()
        if pid is None:
            return

        p = self.db.get_prompt(pid, self.profile_id)
        if not p:
            return

        types = [name for _, name in self.db.list_types(self.profile_id)]
        dlg = PromptDialog(types, self.icon, self.theme, existing=p)
        center_dialog(dlg, self)

        if dlg.exec() != QDialog.Accepted:
            return

        while True:
            try:
                self.db.upsert_prompt(self.profile_id, pid, **dlg.data())
                break
            except Exception as exc:
                logging.getLogger(__name__).exception("Не удалось сохранить промт")
                QMessageBox.critical(self, "Ошибка сохранения", str(exc))
                if dlg.exec() != QDialog.Accepted:
                    return
        self.refresh_all()
        self.select_prompt(pid)

    def delete_prompt(self) -> None:
        pid = self.selected_prompt_id()
        if pid is None:
            return

        r = QMessageBox.question(
            self,
            "Удалить",
            "Вы уверены?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return

        self.db.delete_prompt(self.profile_id, pid)
        self.refresh_all()

    def export_prompts(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить выгрузку",
            "prompts_export.txt",
            "Текстовые файлы (*.txt)",
        )
        if not path:
            return

        type_id = self.current_type_id()
        prompts = self.db.list_prompts(self.profile_id, type_id, self.search.text())

        header = [
            f"{APP_NAME} — экспорт промтов",
            f"Профиль: {self.profile_name}",
            f"Дата: {now_iso()}",
            f"Фильтр: {'Все категории' if type_id is None else self.db.get_type_name(self.profile_id, type_id)}",
            f"Поиск: {self.search.text()}",
            "=" * 60,
            "",
        ]

        blocks: list[str] = []
        for p in prompts:
            blocks.append(self.render_prompt_text(p))
            blocks.append("-" * 60)
            blocks.append("")

        content = "\n".join(header + blocks).rstrip() + "\n"

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            QMessageBox.information(self, "Готово", f"Выгрузил:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка!", f"Не смог сохранить файл:\n{e}")

    def render_prompt_text(self, p: Prompt) -> str:
        return "\n".join(
            [
                f"Название: {p.name}",
                "",
                f"Категория: {p.type}",
                "",
                f"Модель: {p.model}",
                "",
                f"LoRA: {p.lora}".rstrip(),
                "",
                "",
                f"Описание: {p.description}",
                "",
                "",
                "Positive:",
                p.positive,
                "",
                "",
                "Negative:",
                p.negative,
                "",
            ]
        )
