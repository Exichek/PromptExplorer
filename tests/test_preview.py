"""Проверки миниатюр, обновления старой базы и переноса картинок вместе с данными."""

import sqlite3
from contextlib import closing

import pytest
from PySide6.QtGui import QColor, QImage

from promptexplorer.db import DB, MAX_PREVIEW_BYTES, SCHEMA_VERSION
from promptexplorer.ui.image_preview import thumbnail_from_file


@pytest.fixture
def art(tmp_path, qapp):
    path = tmp_path / "пример.png"
    image = QImage(1800, 1200, QImage.Format_RGB32)
    image.fill(QColor("#37598b"))
    assert image.save(str(path))
    return path


def new_prompt(db):
    profile = db.create_profile("Работа")
    pid = db.upsert_prompt(profile, None, "", "Пример", "", "", "", "", "")
    return profile, pid


@pytest.mark.parametrize("format", ["PNG", "JPEG", "WEBP"])
def test_image_formats_are_normalized_to_small_png(tmp_path, qapp, format):
    path = tmp_path / ("art." + format.lower())
    image = QImage(1800, 1200, QImage.Format_RGB32)
    image.fill(QColor("#285d74"))
    assert image.save(str(path), format)
    data = thumbnail_from_file(str(path))
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    restored = QImage.fromData(data)
    assert max(restored.width(), restored.height()) == 512
    assert abs(restored.width() / restored.height() - 1.5) < 0.01


def test_small_image_is_not_upscaled(tmp_path, qapp):
    path = tmp_path / "small.png"
    image = QImage(40, 80, QImage.Format_RGB32)
    image.fill(QColor("red"))
    assert image.save(str(path))
    restored = QImage.fromData(thumbnail_from_file(str(path)))
    assert restored.size() == image.size()


def test_invalid_and_missing_image_are_rejected(tmp_path):
    invalid = tmp_path / "broken.jpg"
    invalid.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        thumbnail_from_file(str(invalid))
    with pytest.raises(OSError):
        thumbnail_from_file(str(tmp_path / "missing.png"))


def test_preview_survives_original_deletion_edit_backup_and_import(db, art, tmp_path):
    profile, pid = new_prompt(db)
    data = thumbnail_from_file(str(art))
    db.set_prompt_preview(profile, pid, data)
    art.unlink()
    db.upsert_prompt(profile, pid, "", "Новое название", "", "", "", "", "")
    assert db.get_prompt(pid, profile).preview == data
    # Список не загружает все BLOB в память, изображение нужно только выбранному промту.
    assert db.list_prompts(profile)[0].preview is None
    backup = db.backup_to(tmp_path / "with-preview.sqlite3")
    with closing(DB(str(backup))) as copied:
        assert copied.get_prompt(pid, profile).preview == data
    imported = db.import_profile_from_db(str(backup), profile)
    imported_id = db.list_prompts(imported)[0].id
    assert db.get_prompt(imported_id, imported).preview == data
    db.set_prompt_preview(imported, imported_id, None)
    assert db.get_prompt(imported_id, imported).preview is None
    assert db.get_prompt(pid, profile).preview == data


def test_preview_cannot_be_changed_from_another_profile(db, art):
    profile, pid = new_prompt(db)
    data = thumbnail_from_file(str(art))
    db.set_prompt_preview(profile, pid, data)
    other = db.create_profile("Другой")
    with pytest.raises(ValueError):
        db.set_prompt_preview(other, pid, None)
    assert db.get_prompt(pid, profile).preview == data


@pytest.mark.parametrize("invalid", ["текст", b"x" * (MAX_PREVIEW_BYTES + 1)])
def test_invalid_preview_does_not_replace_existing_image(db, art, invalid):
    profile, pid = new_prompt(db)
    data = thumbnail_from_file(str(art))
    db.set_prompt_preview(profile, pid, data)
    with pytest.raises(ValueError):
        db.set_prompt_preview(profile, pid, invalid)
    assert db.get_prompt(pid, profile).preview == data


def test_migration_from_schema_one_keeps_ids_and_creates_backup(tmp_path):
    path = tmp_path / "version1.sqlite3"
    with closing(DB(str(path))) as original:
        profile, pid = new_prompt(original)
        types = original.list_types(profile)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("ALTER TABLE prompts DROP COLUMN preview")
        conn.execute("ALTER TABLE prompts DROP COLUMN metadata")
        conn.execute("PRAGMA user_version=1")
    with closing(sqlite3.connect(path)) as conn:
        before = list(conn.iterdump())
    with closing(DB(str(path))) as migrated:
        assert migrated.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert migrated.list_types(profile) == types
        assert migrated.get_prompt(pid, profile).name == "Пример"
        assert migrated.get_prompt(pid, profile).preview is None
        with closing(sqlite3.connect(migrated.last_migration_backup)) as backup:
            assert list(backup.iterdump()) == before


def test_oversized_imported_preview_rolls_back_whole_profile(db, tmp_path):
    source_path = tmp_path / "external.sqlite3"
    with closing(DB(str(source_path))) as source:
        profile, pid = new_prompt(source)
        with source.conn:
            source.conn.execute(
                "UPDATE prompts SET preview=? WHERE id=?", (b"x" * (MAX_PREVIEW_BYTES + 1), pid)
            )
    with pytest.raises(ValueError):
        db.import_profile_from_db(str(source_path), profile)
    assert db.list_profiles() == []
    assert db.conn.execute("SELECT count(*) FROM types").fetchone()[0] == 0
