"""Хранилище SQLite: атомарные операции, миграции и импорт без изменения источника."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import Prompt
from .paths import now_iso

SCHEMA_VERSION = 1
FIELDS = (
    "name",
    "description",
    "positive",
    "negative",
    "lora",
    "model",
    "created_at",
    "updated_at",
)
SELECT = """SELECT p.id,t.name AS type,p.name,p.description,p.positive,p.negative,
    p.lora,p.model,p.created_at,p.updated_at FROM prompts p
    JOIN types t ON t.id=p.type_id AND t.profile_id=p.profile_id"""


def _snapshot(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    if conn.execute("PRAGMA user_version").fetchone()[0] > SCHEMA_VERSION:
        raise ValueError("База создана более новой версией PromptExplorer.")
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise ValueError("Нарушена целостность файла базы данных.")
    required = {
        "profiles": {"id", "name", "created_at"},
        "types": {"id", "name"},
        "prompts": {"id", "profile_id", "type_id", *FIELDS},
    }
    result = {}
    for table, columns in required.items():
        actual = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if not columns <= actual:
            raise ValueError(f"Неподдерживаемая структура таблицы {table}.")
        optional = {"profiles": {"theme"}, "types": {"profile_id"}, "prompts": set()}
        if actual - columns - optional[table]:
            raise ValueError(f"Неизвестные поля таблицы {table}; файл не изменён.")
        result[table] = [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
        identifiers = [row["id"] for row in result[table]]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError(f"Повторяющиеся идентификаторы в таблице {table}.")
    return result


@contextmanager
def _external(path: str | Path) -> Iterator[sqlite3.Connection]:
    with closing(
        sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    ) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        yield conn


class DB:
    """Управлять одной локальной базой, проверяя связи и границы транзакций."""

    def __init__(self, path: str | Path) -> None:
        self.path = path
        self.last_migration_backup: Path | None = None
        self.conn = sqlite3.connect(path, timeout=5)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.create_function("casefold", 1, lambda s: s.casefold(), deterministic=True)
        try:
            self._init_schema()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def backup_to(self, path: str | Path) -> Path:
        """Создать согласованную копию SQLite, не перезаписывая существующие файлы."""
        target = Path(path).resolve()
        if self.path != ":memory:" and target == Path(self.path).resolve():
            raise ValueError("Выберите другой путь для резервной копии.")
        with target.open("xb"):
            pass
        try:
            with closing(sqlite3.connect(target)) as backup:
                self.conn.backup(backup)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target

    def _create_schema(self) -> None:
        for sql in [
            """CREATE TABLE profiles(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,
               theme TEXT NOT NULL DEFAULT 'light',created_at TEXT NOT NULL)""",
            """CREATE TABLE types(id INTEGER PRIMARY KEY AUTOINCREMENT,
               profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
               name TEXT NOT NULL,UNIQUE(profile_id,name),UNIQUE(id,profile_id))""",
            """CREATE TABLE prompts(id INTEGER PRIMARY KEY AUTOINCREMENT,
               profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
               type_id INTEGER NOT NULL,name TEXT NOT NULL,description TEXT NOT NULL,
               positive TEXT NOT NULL,negative TEXT NOT NULL,lora TEXT NOT NULL,model TEXT NOT NULL,
               created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
               FOREIGN KEY(type_id,profile_id) REFERENCES types(id,profile_id) ON DELETE CASCADE)""",
            "CREATE INDEX prompts_profile_updated ON prompts(profile_id,updated_at DESC,id DESC)",
            "CREATE INDEX prompts_profile_type ON prompts(profile_id,type_id)",
        ]:
            self.conn.execute(sql)

    def _init_schema(self) -> None:
        """Создать схему или перенести старую базу с предварительной копией."""
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise ValueError("База создана более новой версией PromptExplorer.")
        if version == SCHEMA_VERSION:
            if self.conn.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("В базе нарушены связи данных. Восстановите резервную копию.")
            return
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if not tables:
            with self._transaction():
                self._create_schema()
                self.conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            return
        if {r["name"] for r in tables} != {"profiles", "types", "prompts"}:
            raise ValueError("Неподдерживаемая база данных; исходный файл не изменён.")
        if self.path != ":memory:":
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            source = Path(self.path)
            self.last_migration_backup = self.backup_to(
                source.with_name(f"{source.stem}.before-v1-{stamp}-{uuid4().hex[:8]}.sqlite3")
            )
        with self._transaction():
            data = _snapshot(self.conn)
            for table in ("prompts", "types", "profiles"):
                self.conn.execute(f"DROP TABLE {table}")
            self._create_schema()
            for p in data["profiles"]:
                self.conn.execute(
                    "INSERT INTO profiles VALUES(?,?,?,?)",
                    (p["id"], p["name"], p.get("theme", "light"), p["created_at"]),
                )
            categories = {t["id"]: t for t in data["types"]}
            profile_ids = {p["id"] for p in data["profiles"]}
            mapping = {}
            for category in data["types"]:
                owners = [category["profile_id"]] if "profile_id" in category else profile_ids
                for owner in owners:
                    mapping[category["id"], owner] = self._type_id(owner, category["name"])
            for p in data["prompts"]:
                owner, old_type = p["profile_id"], p["type_id"]
                if owner not in profile_ids or old_type not in categories:
                    raise ValueError("Найдены промты без профиля или категории. Миграция отменена.")
                # Исправляем категории, привязанные старой миграцией к профилю 1.
                if (old_type, owner) not in mapping:
                    mapping[old_type, owner] = self._type_id(owner, categories[old_type]["name"])
                self._insert_prompt(owner, mapping[old_type, owner], p, p["id"])
            self.conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    @staticmethod
    def _name(value: str | None) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Название не должно быть пустым.")
        return value

    def _require_profile(self, profile_id: int) -> None:
        if self.get_profile(profile_id) is None:
            raise ValueError("Профиль не найден.")

    def list_profiles(self) -> list[tuple[int, str, str]]:
        return [
            tuple(r) for r in self.conn.execute("SELECT id,name,theme FROM profiles ORDER BY id")
        ]

    def get_profile(self, profile_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()

    def _insert_profile(
        self, name: str, theme: str = "light", created_at: str | None = None
    ) -> int:
        return self.conn.execute(
            "INSERT INTO profiles(name,theme,created_at) VALUES(?,?,?)",
            (self._name(name), theme, created_at or now_iso()),
        ).lastrowid

    def create_profile(self, name: str, theme: str = "light") -> int:
        with self._transaction():
            return self._insert_profile(name, theme)

    def delete_profile(self, profile_id: int) -> None:
        with self._transaction():
            self.conn.execute("DELETE FROM profiles WHERE id=?", (profile_id,))

    def list_types(self, profile_id: int) -> list[tuple[int, str]]:
        return [
            tuple(r)
            for r in self.conn.execute(
                "SELECT id,name FROM types WHERE profile_id=? ORDER BY name COLLATE NOCASE",
                (profile_id,),
            )
        ]

    def get_type_name(self, profile_id: int, type_id: int) -> str:
        row = self.conn.execute(
            "SELECT name FROM types WHERE id=? AND profile_id=?", (type_id, profile_id)
        ).fetchone()
        return row["name"] if row else ""

    def _type_id(self, profile_id: int, name: str) -> int:
        name = self._name(name)
        self.conn.execute(
            "INSERT INTO types(profile_id,name) VALUES(?,?) ON CONFLICT(profile_id,name) DO NOTHING",
            (profile_id, name),
        )
        return self.conn.execute(
            "SELECT id FROM types WHERE profile_id=? AND name=?", (profile_id, name)
        ).fetchone()["id"]

    def create_type_if_missing(self, profile_id: int, name: str) -> int:
        with self._transaction():
            self._require_profile(profile_id)
            return self._type_id(profile_id, name)

    def rename_type(self, profile_id: int, type_id: int, new_name: str) -> None:
        with self._transaction():
            try:
                cursor = self.conn.execute(
                    "UPDATE types SET name=? WHERE id=? AND profile_id=?",
                    (self._name(new_name), type_id, profile_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Категория с таким названием уже есть.") from exc
            if cursor.rowcount != 1:
                raise ValueError("Категория не найдена.")

    def type_prompt_count(self, profile_id: int, type_id: int) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM prompts WHERE profile_id=? AND type_id=?", (profile_id, type_id)
        ).fetchone()[0]

    def delete_type_and_prompts(self, profile_id: int, type_id: int) -> None:
        with self._transaction():
            self.conn.execute(
                "DELETE FROM types WHERE id=? AND profile_id=?", (type_id, profile_id)
            )

    def list_prompts(
        self, profile_id: int, type_id: int | None = None, search: str = ""
    ) -> list[Prompt]:
        """Найти промты профиля; поиск учитывает регистр кириллицы и буквальные символы."""
        sql, args = SELECT + " WHERE p.profile_id=?", [profile_id]
        if type_id is not None:
            sql += " AND p.type_id=?"
            args.append(type_id)
        if search.strip():
            sql += " AND instr(casefold(p.name||' '||t.name||' '||p.description||' '||p.positive||' '||p.negative||' '||p.lora||' '||p.model),casefold(?))>0"
            args.append(search.strip())
        return [
            Prompt(**dict(r))
            for r in self.conn.execute(sql + " ORDER BY p.updated_at DESC,p.id DESC", args)
        ]

    def get_prompt(self, prompt_id: int | None, profile_id: int | None = None) -> Prompt | None:
        sql, args = SELECT + " WHERE p.id=?", [prompt_id]
        if profile_id is not None:
            sql += " AND p.profile_id=?"
            args.append(profile_id)
        row = self.conn.execute(sql, args).fetchone()
        return Prompt(**dict(row)) if row else None

    def _insert_prompt(
        self, profile_id: int, type_id: int, data: dict[str, Any], prompt_id: int | None = None
    ) -> int:
        return self.conn.execute(
            "INSERT INTO prompts(id,profile_id,type_id,name,description,positive,negative,lora,model,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (prompt_id, profile_id, type_id, *(data[field] for field in FIELDS)),
        ).lastrowid

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
        with self._transaction():
            self._require_profile(profile_id)
            name = self._name(name)
            if prompt_id is not None and self.get_prompt(prompt_id, profile_id) is None:
                raise ValueError("Промт не найден в выбранном профиле.")
            type_id = self._type_id(profile_id, type_name.strip() or "Без категории")
            timestamp = now_iso()
            values = (name, description, positive, negative, lora, model, timestamp)
            if prompt_id is None:
                data = dict(zip(FIELDS, (*values[:-1], timestamp, timestamp), strict=True))
                return self._insert_prompt(profile_id, type_id, data)
            self.conn.execute(
                """UPDATE prompts SET type_id=?,name=?,description=?,positive=?,
                negative=?,lora=?,model=?,updated_at=? WHERE id=? AND profile_id=?""",
                (type_id, *values, prompt_id, profile_id),
            )
            return prompt_id

    def delete_prompt(self, profile_id: int, prompt_id: int | None) -> None:
        with self._transaction():
            self.conn.execute(
                "DELETE FROM prompts WHERE id=? AND profile_id=?", (prompt_id, profile_id)
            )

    def stats_total(self, profile_id: int) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM prompts WHERE profile_id=?", (profile_id,)
        ).fetchone()[0]

    def stats_by_type(self, profile_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT t.name,COUNT(p.id) AS count FROM types t
            LEFT JOIN prompts p ON p.type_id=t.id AND p.profile_id=t.profile_id
            WHERE t.profile_id=? GROUP BY t.id ORDER BY count DESC,t.name""",
            (profile_id,),
        ).fetchall()

    @staticmethod
    def read_profiles_from_db(db_path: str | Path) -> list[tuple[int, str, str]]:
        with _external(db_path) as conn:
            data = _snapshot(conn)
            return [(p["id"], p["name"], p.get("theme", "light")) for p in data["profiles"]]

    def import_profile_from_db(self, external_db_path: str | Path, external_profile_id: int) -> int:
        """Импортировать выбранный профиль целиком либо откатить все изменения."""
        with _external(external_db_path) as conn:
            data = _snapshot(conn)
        profile = next((p for p in data["profiles"] if p["id"] == external_profile_id), None)
        if profile is None:
            raise ValueError("Профиль не найден.")
        categories = {t["id"]: t for t in data["types"]}
        with self._transaction():
            new_id = self._insert_profile(
                profile["name"], profile.get("theme", "light"), profile["created_at"]
            )
            mapping = {}
            for category in data["types"]:
                if category.get("profile_id", external_profile_id) == external_profile_id:
                    mapping[category["id"]] = self._type_id(new_id, category["name"])
            for prompt in data["prompts"]:
                if prompt["profile_id"] != external_profile_id:
                    continue
                old_type = prompt["type_id"]
                if old_type not in categories:
                    raise ValueError("В импортируемом профиле есть промт без категории.")
                if old_type not in mapping:
                    mapping[old_type] = self._type_id(new_id, categories[old_type]["name"])
                self._insert_prompt(new_id, mapping[old_type], prompt)
            return new_id
