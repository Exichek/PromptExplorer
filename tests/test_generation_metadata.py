"""Проверки весов LoRA, параметров генерации, переноса базы и оформления плашек."""

import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QLabel, QWidget

from promptexplorer.db import DB, SCHEMA_VERSION
from promptexplorer.metadata import GENERATION_FIELDS, read_metadata
from promptexplorer.ui.dialogs.prompt_dialog import PromptDialog
from promptexplorer.ui.flow_layout import FlowLayout
from promptexplorer.ui.prompt_details import PromptDetails, lora_resources
from promptexplorer.ui.utils import theme_qss


@pytest.mark.parametrize(
    "value,expected",
    [
        ("style:0.4", [("style", "0.4")]),
        ("<lora:style:1.2>", [("style", "1.2")]),
        ("<LORA:style:-0.5>", [("style", "-0.5")]),
        ("style:.4", [("style", "0.4")]),
        ("style:-.4", [("style", "-0.4")]),
        ("style:0", [("style", "0")]),
        ("style:1e-3", [("style", "1e-3")]),
        ("style:0,4, night:1,2", [("style", "0.4"), ("night", "1.2")]),
        ("<lora:style:0,4>", [("style", "0.4")]),
        ("style,night", [("style", None), ("night", None)]),
        ("style:NaN", [("style:NaN", None)]),
        ("https://example.com:443", [("https://example.com:443", None)]),
        ("<lora:unfinished:0.4", [("<lora:unfinished:0.4", None)]),
        (r"C:\loras\style.safetensors", [(r"C:\loras\style.safetensors", None)]),
    ],
)
def test_lora_weight_is_only_extracted_when_explicit(value, expected):
    assert lora_resources(value) == expected


def create_prompt(db, metadata=None):
    profile = db.create_profile("Работа")
    pid = db.upsert_prompt(
        profile, None, "", "Название", "", "Свет", "", "style:0.4", "", metadata=metadata
    )
    return profile, pid


def test_metadata_is_preserved_by_edit_backup_and_import(db, tmp_path):
    metadata = {
        "steps": "40",
        "seed": "9223372036854775807",
        "workflow": "Мой workflow",
        "custom": "<b>значение</b>",
    }
    profile, pid = create_prompt(db, metadata)
    assert db.get_prompt(pid, profile).metadata == metadata
    db.upsert_prompt(profile, pid, "", "Другое название", "", "Свет", "", "style:0.4", "")
    assert db.get_prompt(pid, profile).metadata == metadata
    assert db.list_prompts(profile, search="мой workflow")[0].id == pid
    backup = db.backup_to(tmp_path / "metadata.sqlite3")
    with closing(DB(str(backup))) as copy:
        assert copy.get_prompt(pid, profile).metadata == metadata
    imported = db.import_profile_from_db(backup, profile)
    assert db.list_prompts(imported)[0].metadata == metadata
    db.upsert_prompt(profile, pid, "", "Другое название", "", "", "", "style:0.4", "", metadata={})
    assert db.get_prompt(pid, profile).metadata == {}


@pytest.mark.parametrize("invalid", ["[]", "{broken", {"steps": 40}, [1, 2]])
def test_invalid_metadata_is_rejected(invalid):
    with pytest.raises(ValueError):
        read_metadata(invalid)


@pytest.mark.parametrize("version", [1, 2])
def test_previous_schema_is_upgraded_with_backup(tmp_path, version):
    path = tmp_path / "old.sqlite3"
    with closing(DB(str(path))) as original:
        profile, pid = create_prompt(original)
        original.set_prompt_preview(profile, pid, b"preview bytes")
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("ALTER TABLE prompts DROP COLUMN metadata")
        if version == 1:
            conn.execute("ALTER TABLE prompts DROP COLUMN preview")
        conn.execute(f"PRAGMA user_version={version}")
    with closing(sqlite3.connect(path)) as conn:
        before = list(conn.iterdump())
    with closing(DB(str(path))) as migrated:
        prompt = migrated.get_prompt(pid, profile)
        assert prompt.metadata == {}
        assert prompt.name == "Название"
        assert prompt.preview == (b"preview bytes" if version == 2 else None)
        assert migrated.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        with closing(sqlite3.connect(migrated.last_migration_backup)) as backup:
            assert list(backup.iterdump()) == before


def test_editor_saves_optional_parameters_and_keeps_unknown_fields(qapp, db):
    profile, pid = create_prompt(db, {"seed": "-1", "custom": "Сохранить"})
    dialog = PromptDialog([], QIcon(), "dark", db.get_prompt(pid, profile))
    assert dialog.metadata_inputs["seed"].text() == "-1"
    dialog.metadata_inputs["seed"].clear()
    dialog.metadata_inputs["sampler"].setText("Euler A")
    db.upsert_prompt(profile, pid, **dialog.data())
    assert db.get_prompt(pid, profile).metadata == {"sampler": "Euler A", "custom": "Сохранить"}


def test_card_shows_weight_badges_and_fixed_metadata_font(qapp, db):
    profile, pid = create_prompt(db, {"steps": "40", "sampler": "Euler A"})
    card = PromptDetails()
    card.setStyleSheet(theme_qss("dark"))
    card.set_prompt(db.get_prompt(pid, profile))
    card.resize(420, 700)
    card.show()
    qapp.processEvents()
    assert [
        label.text() for label in card.findChildren(QLabel, "WeightBadge") if not label.isHidden()
    ] == ["0.4"]
    assert card.metadata_flow.count() == 2
    chip = card.metadata_flow.itemAt(0).widget()
    assert all(
        card.metadata_flow.itemAt(i).widget().height()
        <= card.metadata_flow.itemAt(i).widget().fontMetrics().height() + 8
        for i in range(card.metadata_flow.count())
    )
    original_font = qapp.font()
    try:
        qapp.setFont(QFont("Arial", 24))
        qapp.processEvents()
        assert chip.font().pointSizeF() == 8
    finally:
        qapp.setFont(original_font)
        card.close()
    card.set_prompt(replace(db.get_prompt(pid, profile), metadata={}))
    assert card.metadata_box.isHidden()


def test_metadata_badges_wrap_without_overlap(qapp):
    container = QWidget()
    layout = FlowLayout(container)
    for _, caption, _ in GENERATION_FIELDS:
        label = QLabel(caption + ": EXAMPLE")
        label.setWordWrap(True)
        layout.addWidget(label)
    container.resize(240, 500)
    container.show()
    qapp.processEvents()
    narrow = layout.heightForWidth(240)
    assert narrow > layout.heightForWidth(700)
    boxes = [layout.itemAt(i).geometry() for i in range(layout.count())]
    assert all(box.left() >= 0 and box.right() < 240 for box in boxes)
    assert all(not a.intersects(b) for i, a in enumerate(boxes) for b in boxes[i + 1 :])
    container.close()
