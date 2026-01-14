import os
import sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from .constants import APP_NAME


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
