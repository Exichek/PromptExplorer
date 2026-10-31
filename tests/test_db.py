"""Проверки сохранности данных, миграций и изоляции профилей."""

import hashlib
import sqlite3
from contextlib import closing

import pytest

from promptexplorer.db import DB, SCHEMA_VERSION


def add(db, profile, name="Пейзаж", category="Природа", **changes):
    values = dict(
        type_name=category,
        name=name,
        description="Описание",
        positive="ЛЕС, свет",
        negative="Шум",
        lora="Детали",
        model="Модель",
    )
    values.update(changes)
    return db.upsert_prompt(profile, None, **values)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path):
    """Сравнить данные и схему независимо от служебных страниц SQLite."""
    with closing(sqlite3.connect(path)) as conn:
        return list(conn.iterdump())


def test_crud_and_reopen(db):
    profile = db.create_profile("Работа")
    pid = add(db, profile)
    db.upsert_prompt(profile, pid, "Новая", "Изменён", "", "Свет", "", "", "Модель")
    assert db.get_prompt(pid, profile).name == "Изменён"
    with closing(DB(db.path)) as reopened:
        assert reopened.get_prompt(pid).positive == "Свет"
    db.delete_prompt(profile, pid)
    assert db.stats_total(profile) == 0


def test_missing_profile_and_prompt_do_not_create_categories(db):
    with pytest.raises(ValueError):
        add(db, 999)
    profile = db.create_profile("Работа")
    with pytest.raises(ValueError):
        db.upsert_prompt(profile, 999, "Не создавать", "Название", "", "", "", "", "")
    assert db.list_types(profile) == []


def test_profiles_cannot_modify_each_other(db):
    first, second = db.create_profile("Один"), db.create_profile("Два")
    pid = add(db, first)
    with pytest.raises(ValueError):
        db.upsert_prompt(second, pid, "Новая", "Чужой", "", "", "", "", "")
    db.delete_prompt(second, pid)
    assert db.get_prompt(pid, second) is None
    assert db.get_prompt(pid, first).name == "Пейзаж"


def test_foreign_keys_reject_cross_profile_category(db):
    first, second = db.create_profile("Один"), db.create_profile("Два")
    pid = add(db, first)
    category = db.create_type_if_missing(second, "Чужая")
    with pytest.raises(sqlite3.IntegrityError), db.conn:
        db.conn.execute("UPDATE prompts SET type_id=? WHERE id=?", (category, pid))
    assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_profile_and_category_cascade_delete(db):
    profile = db.create_profile("Работа")
    add(db, profile)
    category = db.list_types(profile)[0][0]
    db.delete_type_and_prompts(profile, category)
    assert db.stats_total(profile) == 0
    add(db, profile)
    db.delete_profile(profile)
    assert db.conn.execute("SELECT count(*) FROM prompts").fetchone()[0] == 0
    assert db.conn.execute("SELECT count(*) FROM types").fetchone()[0] == 0


def test_category_uniqueness_and_atomic_save(db):
    profile = db.create_profile("Работа")
    category = db.create_type_if_missing(profile, "Одна")
    assert db.create_type_if_missing(profile, "Одна") == category
    with pytest.raises(sqlite3.IntegrityError):
        add(db, profile, category="Не сохранять", positive=None)
    assert db.list_types(profile) == [(category, "Одна")]


@pytest.mark.parametrize("query", ["лес", "ЛЕС", "описание", "ДЕТАЛИ", "модель", "природа"])
def test_search_cyrillic_and_all_fields(db, query):
    profile = db.create_profile("Работа")
    pid = add(db, profile)
    assert [p.id for p in db.list_prompts(profile, search=query)] == [pid]
    assert db.list_prompts(db.create_profile("Пустой"), search=query) == []


def test_search_treats_wildcards_literally(db):
    profile = db.create_profile("Работа")
    pid = add(db, profile, name="100%_качество")
    add(db, profile, name="Другое")
    assert [p.id for p in db.list_prompts(profile, search="%_")] == [pid]


@pytest.mark.parametrize("old_bug", [False, True])
def test_migration_preserves_profiles_prompts_and_backup(legacy_db, old_bug):
    if old_bug:
        with closing(sqlite3.connect(legacy_db)) as conn, conn:
            conn.execute("ALTER TABLE types ADD COLUMN profile_id INTEGER NOT NULL DEFAULT 1")
    before = dump(legacy_db)
    with closing(DB(str(legacy_db))) as db:
        assert db.get_prompt(20, 2).positive == "Ночь"
        assert db.get_prompt(10, 1).created_at == "2025-01-01 10:00:00"
        assert db.list_types(2)[0][1] == "Общая"
        assert db.conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert dump(db.last_migration_backup) == before
    with closing(DB(str(legacy_db))) as db:
        assert db.last_migration_backup is None
        assert db.stats_total(1) == 1 and db.stats_total(2) == 1


def test_failed_migration_rolls_back_schema_and_data(legacy_db):
    with closing(sqlite3.connect(legacy_db)) as conn, conn:
        conn.execute("UPDATE prompts SET type_id=999 WHERE id=20")
    with pytest.raises(ValueError):
        DB(str(legacy_db))
    with closing(sqlite3.connect(legacy_db)) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM prompts").fetchone()[0] == 2
        assert "profile_id" not in {r[1] for r in conn.execute("PRAGMA table_info(types)")}
    assert list(legacy_db.parent.glob("*.before-v*-*.sqlite3"))


def test_legacy_import_preserves_source_and_selected_profile(db, legacy_db):
    before = fingerprint(legacy_db)
    assert len(DB.read_profiles_from_db(str(legacy_db))) == 2
    profile = db.import_profile_from_db(str(legacy_db), 2)
    assert db.stats_total(profile) == 1
    assert db.list_prompts(profile)[0].name == "Второй промт"
    assert fingerprint(legacy_db) == before


def test_current_import_and_backup(db, tmp_path):
    profile = db.create_profile("Работа")
    pid = add(db, profile)
    backup = db.backup_to(tmp_path / "backup.sqlite3")
    with closing(DB(str(backup))) as source:
        assert source.get_prompt(pid).positive == "ЛЕС, свет"
    imported = db.import_profile_from_db(str(backup), profile)
    assert db.stats_total(imported) == 1
    with pytest.raises(FileExistsError):
        db.backup_to(backup)
    with pytest.raises(ValueError):
        db.backup_to(db.path)


def test_failed_import_rolls_back_even_after_insert(db, legacy_db):
    with closing(sqlite3.connect(legacy_db)) as conn, conn:
        conn.execute("UPDATE prompts SET type_id=999 WHERE id=20")
    before = fingerprint(legacy_db)
    with pytest.raises(ValueError):
        db.import_profile_from_db(str(legacy_db), 2)
    assert db.list_profiles() == []
    assert db.conn.execute("SELECT count(*) FROM types").fetchone()[0] == 0
    assert fingerprint(legacy_db) == before
    legacy_db.unlink()  # В Windows обнаруживает незакрытые соединения после ошибки.


def test_missing_import_file_is_not_created(db, tmp_path):
    path = tmp_path / "missing.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        db.import_profile_from_db(str(path), 1)
    assert not path.exists()


def test_future_schema_is_rejected_without_changes(tmp_path):
    path = tmp_path / "future.sqlite3"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA user_version=999")
    before = fingerprint(path)
    with pytest.raises(ValueError):
        DB(str(path))
    assert fingerprint(path) == before


def test_unknown_database_is_not_modified(tmp_path):
    path = tmp_path / "foreign.sqlite3"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE other(value TEXT)")
    before = fingerprint(path)
    with pytest.raises(ValueError):
        DB(str(path))
    assert fingerprint(path) == before


def test_migration_refuses_unknown_fields_without_data_loss(legacy_db):
    with closing(sqlite3.connect(legacy_db)) as conn, conn:
        conn.execute("ALTER TABLE prompts ADD COLUMN custom TEXT DEFAULT 'Личные данные'")
    before = fingerprint(legacy_db)
    with pytest.raises(ValueError):
        DB(str(legacy_db))
    assert fingerprint(legacy_db) == before


@pytest.mark.parametrize("category", ["", "   "])
def test_empty_category_is_optional_and_survives_reopen(db, category):
    profile = db.create_profile("Работа")
    pid = db.upsert_prompt(profile, None, category, "Название", "", "", "", "", "")
    with closing(DB(db.path)) as reopened:
        saved = reopened.get_prompt(pid, profile)
        assert saved.name == "Название"
        assert saved.type == "Без категории"
        assert saved.model == ""
