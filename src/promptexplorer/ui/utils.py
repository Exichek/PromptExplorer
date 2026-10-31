import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QWidget


def resource_path(rel_path: str) -> str:
    """Найти ресурс пакета в исходниках, установленном wheel или сборке PyInstaller."""
    return str(Path(__file__).resolve().parents[1] / rel_path)


def center_dialog(dlg: QDialog, parent: QWidget | None = None) -> None:

    screen = (parent.screen() if parent else QApplication.primaryScreen()).availableGeometry()
    dlg.adjustSize()
    dlg.resize(min(dlg.width(), screen.width()), min(dlg.height(), screen.height()))

    if parent:
        g = parent.frameGeometry()
        dlg.move(g.center() - dlg.rect().center())
    else:
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
        bg = "#15171c"
        card = "#23262d"
        field = "#1b1e24"
        border = "#343943"
        text = "#e8eaf0"
        hint = "#a0a8b8"
        tab_bg = "#1b1e24"
        tab_sel = "#2c3441"
        hover = "#303744"
        sel_bg = "#294562"
        sel_text = "#ffffff"
        splitter = "#343943"
        menu_bg = "#23262d"
        accent = "#82c8ff"
        badge_bg = "#223b50"
    else:
        bg = "#eef1f6"
        card = "#ffffff"
        field = "#f7f9fc"
        border = "#dce2eb"
        text = "#252936"
        hint = "#697386"
        tab_bg = "#f7f7f7"
        tab_sel = "#ffffff"
        hover = "#f6f6f6"
        sel_bg = "#dceeff"
        sel_text = "#000000"
        splitter = "#e5e5e5"
        menu_bg = "#ffffff"
        accent = "#22689c"
        badge_bg = "#e3f0fb"

    return f"""
    QWidget {{
        color: {text};
        font-size: 10.5pt;
        font-family: "Segoe UI";
    }}

    QMainWindow, QDialog {{
        background: {bg};
    }}

    QScrollArea, QScrollArea > QWidget > QWidget {{
        background: {bg};
        border: 0px;
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
        padding: 6px 10px;
        min-height: 28px;
    }}
    QPushButton:hover {{
        background: {hover};
    }}
    QPushButton:pressed {{
        background: {field};
    }}

    /* Переключение темы */
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

    QLabel#Preview {{
        background: {field};
        border: 1px solid {border};
        border-radius: 10px;
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

    QScrollArea#PromptDetails {{
        background: {card};
        border: 1px solid {border};
        border-radius: 12px;
    }}
    QWidget#PromptSurface {{ background: {card}; }}
    QLabel#PromptTitle {{ font-size: 17pt; font-weight: 600; color: {text}; }}
    QLabel#SectionTitle {{ font-size: 11pt; font-weight: 600; color: {text}; }}
    QLabel#PromptText {{ color: {hint}; }}
    QLabel#ResourceName {{ color: {text}; }}
    QLabel#ResourceBadge {{
        background: {badge_bg}; color: {accent}; border-radius: 4px;
        padding: 3px 7px; font-size: 8pt; font-weight: 600;
    }}
    QFrame#SectionSeparator {{ background: {border}; border: none; }}
    QPushButton#CopyButton, QPushButton#TextToggle {{
        color: {accent}; background: transparent; border: none;
        min-height: 20px; padding: 2px 4px; font-size: 9pt;
    }}
    QPushButton#CopyButton:hover, QPushButton#TextToggle:hover {{ background: {badge_bg}; }}
    QPushButton#CopyButton:disabled {{ color: {hint}; }}
    QScrollBar:vertical {{ background: {card}; width: 9px; margin: 0px; }}
    QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 28px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    """
