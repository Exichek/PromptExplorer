"""Общие фикстуры: только временные базы и изолированный интерфейс Qt."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from promptexplorer.db import DB


@pytest.fixture
def db(tmp_path):
    store = DB(str(tmp_path / "library.sqlite3"))
    yield store
    store.close()


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def legacy_db(tmp_path):
    """Создать старую базу с общей категорией и двумя профилями."""
    import sqlite3

    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE profiles(id INTEGER PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL);
            INSERT INTO profiles VALUES(1,'Первый','2025-01-01 10:00:00');
            INSERT INTO profiles VALUES(2,'Второй','2025-01-02 10:00:00');
            CREATE TABLE types(id INTEGER PRIMARY KEY,name TEXT NOT NULL);
            INSERT INTO types VALUES(1,'Общая');
            CREATE TABLE prompts(id INTEGER PRIMARY KEY,profile_id INTEGER,type_id INTEGER,
                name TEXT NOT NULL,description TEXT NOT NULL,positive TEXT NOT NULL,
                negative TEXT NOT NULL,lora TEXT NOT NULL,model TEXT NOT NULL,
                created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            INSERT INTO prompts VALUES(10,1,1,'Первый промт','Описание','Пейзаж','Шум','LoRA','Модель',
                '2025-01-01 10:00:00','2025-01-01 11:00:00');
            INSERT INTO prompts VALUES(20,2,1,'Второй промт','','Ночь','','','Модель',
                '2025-01-02 10:00:00','2025-01-02 11:00:00');
        """)
    conn.close()
    return path
