# ============================================================
# PromptExplorer — single-file version 0.9.0.0 beta
# ============================================================


import os
import sys
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt, QPoint, QSize, QSettings
from PySide6.QtGui import QIcon, QFont, QPixmap, QCursor
from PySide6.QtWidgets import (
    QApplication,
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
    QLineEdit,
    QPlainTextEdit,
    QMessageBox,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QFileDialog,
    QTabWidget,
    QInputDialog,
    QComboBox,
    QToolBar,
    QMenu,
    QSizePolicy,
    QToolTip,
    QCompleter,
)

# ============================================================
# App constants / UI constants
# ============================================================

APP_NAME = "PromptExplorer"
ORG_NAME = "PromptExplorer"

THEME_ICON_PX = 44
THEME_BTN_SIZE = 48


DB_FILENAME = "promptexplorer.sqlite3"


# ============================================================
# Utils
# ============================================================

def resource_path(rel_path: str) -> str:

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)

        p1 = os.path.join(exe_dir, rel_path)
        if os.path.exists(p1):
            return p1

        base = getattr(sys, "_MEIPASS", exe_dir)
        p2 = os.path.join(base, rel_path)

        return p2 if os.path.exists(p2) else p1

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)


def app_data_dir() -> str:
    if os.name == "nt":
        base = os.getenv("APPDATA") or os.path.expanduser(r"~\AppData\Roaming")
        path = os.path.join(base, APP_NAME)
    else:
        path = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")

    os.makedirs(path, exist_ok=True)
    return path


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def center_dialog(dlg: QDialog, parent: QWidget | None = None) -> None:

    dlg.adjustSize()

    if parent:
        g = parent.frameGeometry()
        dlg.move(g.center() - dlg.rect().center())
    else:
        screen = QApplication.primaryScreen().availableGeometry()
        dlg.move(screen.center() - dlg.rect().center())


def load_hidpi_icon(filename: str, logical_size: int) -> QIcon | None:

    path = resource_path(filename)
    if not os.path.exists(path):
        return None

    pm = QPixmap(path)
    if pm.isNull():
        return None

    scr = QApplication.primaryScreen()
    dpr = scr.devicePixelRatio() if scr else 1.0

    target = int(logical_size * dpr)
    scaled = pm.scaled(target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    scaled.setDevicePixelRatio(dpr)

    return QIcon(scaled)


def theme_qss(theme: str) -> str:
    if theme == "dark":
        bg = "#121212"
        card = "#1b1b1b"
        field = "#181818"
        border = "#2a2a2a"
        text = "#e7e7e7"
        hint = "#bdbdbd"
        tab_bg = "#171717"
        tab_sel = "#1f1f1f"
        hover = "#202020"
        sel_bg = "#2f4d7a"
        sel_text = "#ffffff"
        splitter = "#2a2a2a"
        menu_bg = "#1d1d1d"
    else:
        bg = "#f3f3f3"
        card = "#ffffff"
        field = "#ffffff"
        border = "#dcdcdc"
        text = "#111111"
        hint = "#222222"
        tab_bg = "#f7f7f7"
        tab_sel = "#ffffff"
        hover = "#f6f6f6"
        sel_bg = "#cfe5ff"
        sel_text = "#000000"
        splitter = "#e5e5e5"
        menu_bg = "#ffffff"

    return f"""
    QWidget {{
        color: {text};
        font-size: 10.5pt;
        font-family: "Segoe UI";
    }}

    QMainWindow, QDialog {{
        background: {bg};
    }}

    QWidget#Card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 12px;
    }}

    QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QTreeWidget, QComboBox {{
        color: {text};
        background: {field};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 8px;
        selection-background-color: {sel_bg};
        selection-color: {sel_text};
    }}

    QComboBox::drop-down {{
        border: 0px;
        width: 26px;
    }}

    QPushButton {{
        color: {text};
        background: {card};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 8px 12px;
        min-height: 34px;
    }}
    QPushButton:hover {{
        background: {hover};
    }}
    QPushButton:pressed {{
        background: {field};
    }}

    /* Theme toggle button */
    QPushButton#ThemeBtn {{
        min-height: 0px;
        padding: 0px;
        border-radius: 16px;
        border: 1px solid {border};
        background: {card};
    }}
    QPushButton#ThemeBtn:hover {{
        background: {hover};
    }}
    QPushButton#ThemeBtn:pressed {{
        background: {field};
    }}

    QTabWidget::pane {{
        border: 0px;
        margin-top: 8px;
    }}
    QTabBar::tab {{
        color: {text};
        background: {tab_bg};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 8px 14px;
        margin-right: 6px;
    }}
    QTabBar::tab:selected {{
        background: {tab_sel};
    }}

    QListWidget::item, QTreeWidget::item {{
        padding: 6px;
        border-radius: 8px;
    }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background: {sel_bg};
        color: {sel_text};
    }}

    QLabel#Hint {{
        color: {hint};
    }}

    QSplitter::handle {{
        background: {splitter};
    }}

    QMenu {{
        background: {menu_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 12px;
        border-radius: 8px;
    }}
    QMenu::item:selected {{
        background: {sel_bg};
        color: {sel_text};
    }}

    QToolBar {{
        border: 0px;
        background: transparent;
        spacing: 8px;
    }}
    """


# ============================================================
# Data model
# ============================================================

@dataclass
class Prompt:
    """Объект промта"""
    id: int
    type: str
    name: str
    description: str
    positive: str
    negative: str
    lora: str
    model: str
    created_at: str
    updated_at: str


# ============================================================
# Database layer (SQLite)
# ============================================================

class DB:

    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _col_exists(self, table: str, col: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table});")
        return any(r["name"] == col for r in cur.fetchall())

    def _init_schema(self) -> None:
        cur = self.conn.cursor()

        # Профили
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profiles(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                theme TEXT NOT NULL DEFAULT 'light',
                created_at TEXT NOT NULL
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS types(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS prompts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                type_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                positive TEXT NOT NULL,
                negative TEXT NOT NULL,
                lora TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id),
                FOREIGN KEY(type_id) REFERENCES types(id)
            );
        """)

        self.conn.commit()

        # ---- Migrations for older DB versions ----
        if not self._col_exists("profiles", "theme"):
            cur.execute("ALTER TABLE profiles ADD COLUMN theme TEXT NOT NULL DEFAULT 'light';")
            self.conn.commit()

        if not self._col_exists("types", "profile_id"):
            cur.execute("ALTER TABLE types ADD COLUMN profile_id INTEGER NOT NULL DEFAULT 1;")
            self.conn.commit()

    # ---------------------------
    # Profiles
    # ---------------------------

    def list_profiles(self) -> list[tuple[int, str, str]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, theme FROM profiles ORDER BY id ASC;")
        rows = cur.fetchall()
        out: list[tuple[int, str, str]] = []
        for r in rows:
            theme = r["theme"] if "theme" in r.keys() else "light"
            out.append((int(r["id"]), str(r["name"]), str(theme)))
        return out

    def create_profile(self, name: str, theme: str = "light") -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO profiles(name, theme, created_at) VALUES(?, ?, ?);",
            (name, theme, now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def delete_profile(self, profile_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM prompts WHERE profile_id=?;", (profile_id,))
        cur.execute("DELETE FROM types WHERE profile_id=?;", (profile_id,))
        cur.execute("DELETE FROM profiles WHERE id=?;", (profile_id,))
        self.conn.commit()

    def get_profile(self, profile_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM profiles WHERE id=?;", (profile_id,))
        return cur.fetchone()

    # ---------------------------
    # Types / Categories
    # ---------------------------

    def list_types(self, profile_id: int) -> list[tuple[int, str]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name FROM types WHERE profile_id=? ORDER BY name COLLATE NOCASE;",
            (profile_id,),
        )
        return [(int(r["id"]), str(r["name"])) for r in cur.fetchall()]

    def get_type_name(self, profile_id: int, type_id: int) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM types WHERE id=? AND profile_id=?;", (type_id, profile_id))
        r = cur.fetchone()
        return str(r["name"]) if r else ""

    def create_type_if_missing(self, profile_id: int, name: str) -> int:
        name = (name or "").strip()
        if not name:
            raise ValueError("Empty type name")

        cur = self.conn.cursor()
        cur.execute("SELECT id FROM types WHERE profile_id=? AND name=?;", (profile_id, name))
        row = cur.fetchone()
        if row:
            return int(row["id"])

        cur.execute("INSERT INTO types(profile_id, name) VALUES(?, ?);", (profile_id, name))
        self.conn.commit()
        return int(cur.lastrowid)

    def rename_type(self, profile_id: int, type_id: int, new_name: str) -> None:
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Empty type name")

        cur = self.conn.cursor()

        # Проверка уникальности имени
        cur.execute("SELECT id FROM types WHERE profile_id=? AND name=?;", (profile_id, new_name))
        exists = cur.fetchone()
        if exists and int(exists["id"]) != type_id:
            raise ValueError("Type already exists")

        cur.execute("UPDATE types SET name=? WHERE id=? AND profile_id=?;", (new_name, type_id, profile_id))
        self.conn.commit()

    def type_prompt_count(self, profile_id: int, type_id: int) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS c FROM prompts WHERE profile_id=? AND type_id=?;",
            (profile_id, type_id),
        )
        return int(cur.fetchone()["c"])

    def delete_type_and_prompts(self, profile_id: int, type_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM prompts WHERE profile_id=? AND type_id=?;", (profile_id, type_id))
        cur.execute("DELETE FROM types WHERE id=? AND profile_id=?;", (type_id, profile_id))
        self.conn.commit()

    # ---------------------------
    # Prompts
    # ---------------------------

    def list_prompts(self, profile_id: int, type_id: int | None) -> list[Prompt]:

        cur = self.conn.cursor()

        if type_id is None:
            cur.execute("""
                SELECT p.id, t.name AS type, p.name, p.description, p.positive, p.negative, p.lora, p.model,
                       p.created_at, p.updated_at
                FROM prompts p
                JOIN types t ON t.id = p.type_id
                WHERE p.profile_id=?
                ORDER BY p.updated_at DESC;
            """, (profile_id,))
        else:
            cur.execute("""
                SELECT p.id, t.name AS type, p.name, p.description, p.positive, p.negative, p.lora, p.model,
                       p.created_at, p.updated_at
                FROM prompts p
                JOIN types t ON t.id = p.type_id
                WHERE p.profile_id=? AND p.type_id=?
                ORDER BY p.updated_at DESC;
            """, (profile_id, type_id))

        rows = cur.fetchall()
        return [Prompt(**dict(r)) for r in rows]

    def get_prompt(self, prompt_id: int) -> Prompt | None:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT p.id, t.name AS type, p.name, p.description, p.positive, p.negative, p.lora, p.model,
                   p.created_at, p.updated_at
            FROM prompts p
            JOIN types t ON t.id = p.type_id
            WHERE p.id=?;
        """, (prompt_id,))
        r = cur.fetchone()
        return Prompt(**dict(r)) if r else None

    def upsert_prompt(
        self,
        profile_id: int,
        prompt_id: int | None,
        type_name: str,
        name: str,
        description: str,
        positive: str,
        negative: str,
        lora: str,
        model: str,
    ) -> int:

        type_id = self.create_type_if_missing(profile_id, type_name)
        cur = self.conn.cursor()

        if prompt_id is None:
            cur.execute("""
                INSERT INTO prompts(profile_id, type_id, name, description, positive, negative, lora, model, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                profile_id, type_id, name, description, positive, negative, lora, model,
                now_iso(), now_iso(),
            ))
            self.conn.commit()
            return int(cur.lastrowid)

        cur.execute("""
            UPDATE prompts
            SET type_id=?, name=?, description=?, positive=?, negative=?, lora=?, model=?, updated_at=?
            WHERE id=? AND profile_id=?;
        """, (
            type_id, name, description, positive, negative, lora, model,
            now_iso(),
            prompt_id, profile_id,
        ))
        self.conn.commit()
        return int(prompt_id)

    def delete_prompt(self, profile_id: int, prompt_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM prompts WHERE id=? AND profile_id=?;", (prompt_id, profile_id))
        self.conn.commit()

    def stats_total(self, profile_id: int) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM prompts WHERE profile_id=?;", (profile_id,))
        return int(cur.fetchone()["total"])

    # ---------------------------
    # Import profiles from external DB
    # ---------------------------

    @staticmethod
    def read_profiles_from_db(db_path: str) -> list[tuple[int, str, str]]:

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        try:
            cur.execute("SELECT id, name, theme FROM profiles ORDER BY id ASC;")
            rows = cur.fetchall()
            res = []
            for r in rows:
                theme = r["theme"] if "theme" in r.keys() else "light"
                res.append((int(r["id"]), str(r["name"]), str(theme)))
        except sqlite3.OperationalError:
            # Очень старая база без theme
            cur.execute("SELECT id, name FROM profiles ORDER BY id ASC;")
            res = [(int(r["id"]), str(r["name"]), "light") for r in cur.fetchall()]

        conn.close()
        return res

    def import_profile_from_db(self, external_db_path: str, external_profile_id: int) -> int:

        ext = sqlite3.connect(external_db_path)
        ext.row_factory = sqlite3.Row
        ec = ext.cursor()

        # --- profile ---
        try:
            ec.execute("SELECT id, name, theme FROM profiles WHERE id=?;", (external_profile_id,))
            p = ec.fetchone()
            if not p:
                raise ValueError("Profile not found")
            theme = p["theme"] if "theme" in p.keys() else "light"
            new_profile_id = self.create_profile(str(p["name"]), theme)
        except sqlite3.OperationalError:
            ec.execute("SELECT id, name FROM profiles WHERE id=?;", (external_profile_id,))
            p = ec.fetchone()
            if not p:
                raise ValueError("Profile not found")
            new_profile_id = self.create_profile(str(p["name"]), "light")

        # узнаём структуру types (есть ли profile_id)
        ec.execute("PRAGMA table_info(types);")
        type_cols = [r["name"] for r in ec.fetchall()]
        has_type_profile = "profile_id" in type_cols

        # --- types ---
        if has_type_profile:
            ec.execute("SELECT id, name FROM types WHERE profile_id=?;", (external_profile_id,))
        else:
            ec.execute("SELECT id, name FROM types;")

        old_to_new_type: dict[int, int] = {}
        for r in ec.fetchall():
            new_tid = self.create_type_if_missing(new_profile_id, str(r["name"]))
            old_to_new_type[int(r["id"])] = new_tid

        # --- prompts ---
        ec.execute("""
            SELECT id, type_id, name, description, positive, negative, lora, model, created_at, updated_at
            FROM prompts
            WHERE profile_id=?;
        """, (external_profile_id,))
        rows = ec.fetchall()

        cur = self.conn.cursor()
        for r in rows:
            old_tid = int(r["type_id"])
            new_tid = old_to_new_type.get(old_tid) or self.create_type_if_missing(new_profile_id, "Imported")

            cur.execute("""
                INSERT INTO prompts(profile_id, type_id, name, description, positive, negative, lora, model, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                new_profile_id, new_tid,
                str(r["name"]), str(r["description"]),
                str(r["positive"]), str(r["negative"]),
                str(r["lora"]), str(r["model"]),
                str(r["created_at"]), str(r["updated_at"]),
            ))

        self.conn.commit()
        ext.close()
        return int(new_profile_id)


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


# ============================================================
# Dialog: Create / Edit prompt
# ============================================================

class PromptDialog(QDialog):

    def __init__(self, types: list[str], icon: QIcon, theme: str, existing: Prompt | None = None):
        super().__init__()

        self.setWindowTitle("Редактировать промт" if existing else "Новый промт")
        self.setWindowIcon(icon)
        self.setStyleSheet(theme_qss(theme))
        # ---------------------------
        # Type combobox (editable + search)
        # ---------------------------
        self.type = QComboBox()
        self.type.setEditable(True)
        self.type.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # Qt6-правильно
        self.type.setMaxVisibleItems(12)
        self.type.addItems(types)

        if hasattr(self.type, "setAutoCompletion"):
            self.type.setAutoCompletion(False)

        completer = QCompleter(self.type.model(), self.type)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.type.setCompleter(completer)

        le = self.type.lineEdit()
        le.textEdited.connect(lambda txt: self.type.showPopup() if txt.strip() else self.type.hidePopup())
        # ---------------------------
        # Other fields
        # ---------------------------
        self.name = QLineEdit()
        self.model = QLineEdit()

        self.lora = QPlainTextEdit()
        self.description = QPlainTextEdit()
        self.positive = QPlainTextEdit()
        self.negative = QPlainTextEdit()

        self.lora.setMinimumHeight(90)
        self.description.setMinimumHeight(110)
        self.positive.setMinimumHeight(170)
        self.negative.setMinimumHeight(170)

        self.name.setPlaceholderText("Пример: Dragon")
        self.type.setPlaceholderText("Пример: Cowgirl pose")
        self.model.setPlaceholderText("Пример: Xavier")

        self.lora.setPlaceholderText("Через запятую или построчно")
        self.description.setPlaceholderText("Описание: чтобы не запутаться, что это за промт")
        self.positive.setPlaceholderText("Positive: ключевые слова/теги, описание сцены")
        self.negative.setPlaceholderText("Negative: что исключить")
        # ---------------------------
        # Form layout
        # ---------------------------
        form = QFormLayout()
        form.addRow("Name:", self.name)
        form.addRow("Type:", self.type)
        form.addRow("Model:", self.model)
        form.addRow("LoRA:", self.lora)
        form.addRow("Описание:", self.description)
        form.addRow("Positive:", self.positive)
        form.addRow("Negative:", self.negative)

        # Save/Cancel
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._validate_then_accept)
        self.buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.buttons)

        self.setMinimumWidth(640)

        # ---------------------------
        # If editing — prefill the fields
        # ---------------------------
        self.prompt_id: int | None = None
        if existing:
            self.prompt_id = existing.id
            self.name.setText(existing.name)
            self.type.setCurrentText(existing.type)
            self.model.setText(existing.model)
            self.lora.setPlainText(existing.lora)
            self.description.setPlainText(existing.description)
            self.positive.setPlainText(existing.positive)
            self.negative.setPlainText(existing.negative)

    def _validate_then_accept(self) -> None:
        if not self.name.text().strip():
            QMessageBox.warning(self, "Допиши", "Поле Name не заполнено.")
            return
        if not self.type.currentText().strip():
            QMessageBox.warning(self, "Допиши", "Поле Type не заполнено.")
            return
        if not self.model.text().strip():
            QMessageBox.warning(self, "Допиши", "Поле Model не заполнено.")
            return
        self.accept()

    def data(self) -> dict[str, str]:
        return {
            "type_name": self.type.currentText().strip(),
            "name": self.name.text().strip(),
            "model": self.model.text().strip(),
            "lora": self.lora.toPlainText().strip(),
            "description": self.description.toPlainText().strip() or "(без описания)",
            "positive": self.positive.toPlainText().strip(),
            "negative": self.negative.toPlainText().strip(),
        }


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

    app_icon = QIcon(resource_path("app.ico"))
    app.setWindowIcon(app_icon)

    moon_icon = load_hidpi_icon("moon.png", THEME_ICON_PX)
    sun_icon = load_hidpi_icon("sun.png", THEME_ICON_PX)

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


if __name__ == "__main__":
    main()
