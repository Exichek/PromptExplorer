"""Проверки пользовательских сценариев на настоящих виджетах Qt."""

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox

from promptexplorer.ui.dialogs.prompt_dialog import PromptDialog
from promptexplorer.ui.dialogs.startup_dialog import StartupDialog
from promptexplorer.ui.main_window import MainWindow
from promptexplorer.ui.utils import resource_path


@pytest.fixture
def window(qapp, db, tmp_path, monkeypatch):
    profile = db.create_profile("Работа")
    for name, category in [("Первый", "Природа"), ("Второй", "Природа"), ("Третий", "Портрет")]:
        db.upsert_prompt(profile, None, category, name, "", f"Свет {name}", "Шум", "", "Модель")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    widget = MainWindow(db, QIcon(), None, None, profile, settings, "light")
    widget.show()
    qapp.processEvents()
    yield widget
    with monkeypatch.context() as cleanup:
        cleanup.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
        widget.close()
    widget.deleteLater()
    qapp.processEvents()


def test_refresh_keeps_category_and_selection(window):
    category = window.db.list_types(window.profile_id)[0][0]
    for i in range(window.tree.topLevelItemCount()):
        item = window.tree.topLevelItem(i)
        if item.data(0, Qt.UserRole) == category:
            window.tree.setCurrentItem(item)
    window.list.setCurrentRow(window.list.count() - 1)
    selected = window.selected_prompt_id()
    window.refresh_all()
    assert window.current_type_id() == category
    assert window.selected_prompt_id() == selected


def test_search_empty_state_and_copy(window, qapp):
    window.search.setText("второй")
    window.refresh_list()
    assert window.list.count() == 1
    window.copy_prompt_field("positive")
    assert qapp.clipboard().text() == "Свет Второй"
    window.search.setText("Не существует")
    window.refresh_list()
    assert window.list.count() == 0
    assert not window.btn_edit.isEnabled()
    assert not window.copy_positive.isEnabled()
    assert window.detail.toPlainText() == "Ничего не найдено."


def test_profile_switch_clears_previous_context(window):
    profile = window.db.create_profile("Другой")
    window.reload_profiles_into_combo()
    window.search.setText("Первый")
    window.profile_combo.setCurrentIndex(window.profile_combo.findData(profile))
    assert window.profile_id == profile
    assert window.search.text() == ""
    assert window.list.count() == 0
    assert not window.btn_del.isEnabled()


def test_saved_prompt_is_visible_after_category_change(window):
    pid = window.selected_prompt_id()
    window.db.upsert_prompt(
        window.profile_id, pid, "Новая категория", "Изменён", "", "", "", "", "Модель"
    )
    window.search.setText("Не подходит")
    window.refresh_all()
    window.select_prompt(pid)
    assert window.selected_prompt_id() == pid
    assert window.search.text() == ""


def test_theme_and_geometry_are_saved(window, monkeypatch):
    window.toggle_theme()
    assert window.settings.value("ui_theme") == "dark"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    assert window.close()
    assert window.settings.value("window_geometry")
    assert window.settings.value("splitter_state")


@pytest.mark.parametrize("answer", [QMessageBox.Yes, QMessageBox.No, QMessageBox.NoButton])
def test_main_window_closes_only_after_confirmation(window, monkeypatch, answer):
    """Отмена выхода сохраняет окно и настройки; подтверждение разрешает закрытие."""
    questions = []

    def respond(*args):
        questions.append(args)
        return answer

    monkeypatch.setattr(QMessageBox, "question", respond)
    accepted = answer == QMessageBox.Yes
    assert window.close() == accepted
    assert window.isVisible() != accepted
    assert questions[0][2] == "Вы точно хотите закрыть PromptExplorer?"
    assert questions[0][-1] == QMessageBox.No
    assert window.settings.contains("window_geometry") == accepted
    assert window.settings.contains("splitter_state") == accepted


def test_escape_cancels_real_exit_dialog(window, qapp):
    """Escape закрывает вопрос, но оставляет главное окно программы открытым."""
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest

    observed = []

    def cancel():
        dialog = qapp.activeModalWidget()
        observed.append(isinstance(dialog, QMessageBox))
        QTest.keyClick(dialog, Qt.Key_Escape)

    QTimer.singleShot(0, cancel)
    assert not window.close()
    assert observed == [True]
    assert window.isVisible()


def test_resources_and_dialogs(qapp, db, tmp_path, monkeypatch):
    from pathlib import Path

    from PySide6.QtWidgets import QScrollArea

    monkeypatch.setenv("PROMPTEXPLORER_DATA_DIR", str(tmp_path / "данные & тест"))
    assert Path(resource_path("resources/app.ico")).is_file()
    dialog = PromptDialog(["Природа"], QIcon(), "dark")
    assert dialog.findChild(QScrollArea).widgetResizable()
    dialog.close()
    startup = StartupDialog(db, QIcon(), "light")
    assert startup.copy_path_text == str((tmp_path / "данные & тест").resolve())
    assert not startup.btn_continue.isEnabled()
    startup.close()


def test_export_uses_search(window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    output = tmp_path / "export.txt"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: QMessageBox.Ok)
    window.search.setText("Второй")
    window.export_prompts()
    content = output.read_text(encoding="utf-8")
    assert "Название: Второй" in content
    assert "Название: Первый" not in content


def test_editor_does_not_discard_changes_without_confirmation(qapp, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    dialog = PromptDialog(["Категория"], QIcon(), "light")
    dialog.show()
    dialog.name.setText("Несохранённый промт")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)
    dialog.reject()
    assert dialog.isVisible()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    dialog.reject()
    assert not dialog.isVisible()


def test_resources_in_frozen_package(tmp_path, monkeypatch):
    from promptexplorer.ui import utils

    package = tmp_path / "_internal/promptexplorer"
    resource = package / "resources/app.ico"
    resource.parent.mkdir(parents=True)
    resource.write_bytes(b"icon")
    monkeypatch.setattr(utils, "__file__", str(package / "ui/utils.py"))
    assert utils.resource_path("resources/app.ico") == str(resource)
