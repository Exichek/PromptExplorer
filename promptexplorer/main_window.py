from PySide6.QtCore import Qt, QPoint, QSize, QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QLabel,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QDialog,
    QFileDialog,
    QTabWidget,
    QInputDialog,
    QComboBox,
    QToolBar,
    QMenu,
    QSizePolicy,
)

from .constants import APP_NAME, THEME_ICON_PX, THEME_BTN_SIZE
from .db import DB
from .models import Prompt
from .dialogs.prompt_dialog import PromptDialog
from .utils import center_dialog, now_iso, theme_qss


# ============================================================
# Main window
# ============================================================

class MainWindow(QMainWindow):

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
        self.profile_name = prof["name"] if prof else "Unknown"
        self.setWindowTitle(f"{APP_NAME} — {self.profile_name}")
        self.setWindowIcon(icon)

        self.resize(1200, 720)

        self._build_toolbar()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_prompts_tab()
        self._build_stats_tab()

        self.refresh_all()

    # ---------------------------
    # Window close confirmation
    # ---------------------------
    def closeEvent(self, event):
        r = QMessageBox.question(
            self,
            "Закрыть программу?",
            "Вы уверены, что хотите закрыть PromptExplorer?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if r == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    # ---------------------------
    # Theme handling
    # ---------------------------
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
                self.theme_btn.setText("🌙")
        else:
            if self.sun_icon and not self.sun_icon.isNull():
                self.theme_btn.setIcon(self.sun_icon)
                self.theme_btn.setText("")
            else:
                self.theme_btn.setIcon(QIcon())
                self.theme_btn.setText("☀️")

        self.theme_btn.setIconSize(QSize(THEME_ICON_PX, THEME_ICON_PX))
        self.theme_btn.setFixedSize(THEME_BTN_SIZE, THEME_BTN_SIZE)

    def toggle_theme(self) -> None:
        self.theme = "dark" if self.theme == "light" else "light"
        self.settings.setValue("ui_theme", self.theme)
        self.apply_theme()
        self.update_theme_button()

    # ---------------------------
    # Toolbar
    # ---------------------------
    def _build_toolbar(self) -> None:
        tb = QToolBar()
        tb.setMovable(False)

        tb.setMinimumHeight(THEME_BTN_SIZE + 10)
        self.addToolBar(Qt.TopToolBarArea, tb)

        tb.addWidget(QLabel("Профиль: "))

        self.profile_combo = QComboBox()
        tb.addWidget(self.profile_combo)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)

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

        prof = self.db.get_profile(self.profile_id)
        self.profile_name = prof["name"] if prof else "Unknown"
        self.setWindowTitle(f"{APP_NAME} — {self.profile_name}")

        self.refresh_all()

    # ---------------------------
    # UI helpers
    # ---------------------------
    def _wrap_card(self, w: QWidget) -> QWidget:
        card = QWidget()
        card.setObjectName("Card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(w)

        return card

    # ---------------------------
    # Tabs build
    # ---------------------------
    def _build_prompts_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)

        splitter = QSplitter(Qt.Horizontal)

        # ---- left: types ----
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_add_type = QPushButton("＋ Новый тип")
        self.btn_add_type.clicked.connect(self.add_type)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self.on_type_changed)

        # (rename/delete)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_type_context_menu)

        left_layout.addWidget(self.btn_add_type)
        left_layout.addWidget(self.tree)

        # ---- middle: prompts list ----
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.on_prompt_selected)

        # ---- right: buttons + detail ----
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
        r.addWidget(self.detail)

        # ---- splitter composition ----
        splitter.addWidget(self._wrap_card(left_col))
        splitter.addWidget(self._wrap_card(self.list))
        splitter.addWidget(self._wrap_card(right))

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 4)

        layout.addWidget(splitter)
        self.tabs.addTab(page, "Промты")

    def _build_stats_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.stats_label = QLabel("")
        self.stats_label.setObjectName("Hint")
        self.stats_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.stats_list = QListWidget()
        self.stats_list.itemSelectionChanged.connect(self.on_stats_selected)

        self.stats_detail = QTextEdit()
        self.stats_detail.setReadOnly(True)

        layout.addWidget(self._wrap_card(self.stats_label))
        layout.addWidget(self._wrap_card(self.stats_list))
        layout.addWidget(self._wrap_card(self.stats_detail))

        self.tabs.addTab(page, "Статистика")

    # ---------------------------
    # Types / category logic
    # ---------------------------
    def refresh_types(self) -> None:
        self.tree.clear()

        # All: type_id = None
        all_item = QTreeWidgetItem(["All"])
        all_item.setData(0, Qt.UserRole, None)
        self.tree.addTopLevelItem(all_item)

        for tid, name in self.db.list_types(self.profile_id):
            it = QTreeWidgetItem([name])
            it.setData(0, Qt.UserRole, tid)
            self.tree.addTopLevelItem(it)

        self.tree.expandAll()
        self.tree.setCurrentItem(all_item)

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

    # ---------------------------
    # Prompts list / detail / stats
    # ---------------------------
    def refresh_list(self) -> None:
        self.list.clear()

        type_id = self.current_type_id()
        prompts = self.db.list_prompts(self.profile_id, type_id)

        for p in prompts:
            it = QListWidgetItem(f"[{p.type}] {p.name}")
            it.setData(Qt.UserRole, p.id)
            self.list.addItem(it)

        if self.list.count() > 0:
            self.list.setCurrentRow(0)
        else:
            self.detail.setPlainText("Создайте промт.")

    def refresh_stats(self) -> None:
        total = self.db.stats_total(self.profile_id)
        self.stats_label.setText(f"Профиль: {self.profile_name}\nВсего промтов: {total}")

        self.stats_list.clear()
        for p in self.db.list_prompts(self.profile_id, None):
            it = QListWidgetItem(f"[{p.type}] {p.name}")
            it.setData(Qt.UserRole, p.id)
            self.stats_list.addItem(it)

        if self.stats_list.count() == 0:
            self.stats_detail.setPlainText("Пока пусто.")
        else:
            self.stats_list.setCurrentRow(0)

    def refresh_all(self) -> None:
        self.refresh_types()
        self.refresh_list()
        self.refresh_stats()

    def on_type_changed(self) -> None:
        self.refresh_list()

    def on_prompt_selected(self, current: QListWidgetItem, prev: QListWidgetItem) -> None:
        if not current:
            return
        pid = int(current.data(Qt.UserRole))
        p = self.db.get_prompt(pid)
        self.detail.setPlainText(self.render_prompt_text(p) if p else "Промт не найден.")

    def on_stats_selected(self) -> None:
        item = self.stats_list.currentItem()
        if not item:
            return
        pid = int(item.data(Qt.UserRole))
        p = self.db.get_prompt(pid)
        self.stats_detail.setPlainText(self.render_prompt_text(p) if p else "Промт не найден.")

    def selected_prompt_id(self) -> int | None:
        item = self.list.currentItem()
        return int(item.data(Qt.UserRole)) if item else None

    # ---------------------------
    # CRUD for prompts
    # ---------------------------
    def create_prompt(self) -> None:
        types = [name for _, name in self.db.list_types(self.profile_id)]
        dlg = PromptDialog(types, self.icon, self.theme, existing=None)
        center_dialog(dlg, self)

        if dlg.exec() != QDialog.Accepted:
            return

        d = dlg.data()
        self.db.upsert_prompt(self.profile_id, None, **d)
        self.refresh_all()

    def edit_prompt(self) -> None:
        pid = self.selected_prompt_id()
        if pid is None:
            return

        p = self.db.get_prompt(pid)
        if not p:
            return

        types = [name for _, name in self.db.list_types(self.profile_id)]
        dlg = PromptDialog(types, self.icon, self.theme, existing=p)
        center_dialog(dlg, self)

        if dlg.exec() != QDialog.Accepted:
            return

        d = dlg.data()
        self.db.upsert_prompt(self.profile_id, pid, **d)
        self.refresh_all()

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

    # ---------------------------
    # Export
    # ---------------------------
    def export_prompts(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить выгрузку",
            "prompts_export.txt",
            "Text files (*.txt)",
        )
        if not path:
            return

        type_id = self.current_type_id()
        prompts = self.db.list_prompts(self.profile_id, type_id)

        header = [
            f"{APP_NAME} — экспорт промтов",
            f"Профиль: {self.profile_name}",
            f"Дата: {now_iso()}",
            f"Фильтр: {'All' if type_id is None else self.db.get_type_name(self.profile_id, type_id)}",
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

    # ---------------------------
    # Render helper
    # ---------------------------
    def render_prompt_text(self, p: Prompt) -> str:
        return "\n".join([
            f"Name: {p.name}",
            "",
            f"Type: {p.type}",
            "",
            f"Model: {p.model}",
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
        ])
