import sqlite3

from .models import Prompt
from .utils import now_iso


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
