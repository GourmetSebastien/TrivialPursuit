import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from .models import PLAYER_PALETTE, THEME_PALETTE, Player, Question, Theme

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trivial.db"

DEFAULT_SETTINGS = {
    "sound_enabled": "1",
    "volume": "80",
    "wheel_duration_ms": "3000",
    "avoid_repeats": "1",
    "fullscreen": "0",
    "ui_theme": "dark",
}


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme_id INTEGER NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self._conn.commit()
        for key, value in DEFAULT_SETTINGS.items():
            self._conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value)
            )
        self._conn.commit()

    # ---------- Themes ----------

    def list_themes(self) -> List[Theme]:
        rows = self._conn.execute("SELECT * FROM themes ORDER BY name").fetchall()
        return [Theme(id=r["id"], name=r["name"], color=r["color"]) for r in rows]

    def next_theme_color(self) -> str:
        used = {t.color for t in self.list_themes()}
        for color in THEME_PALETTE:
            if color not in used:
                return color
        count = len(used)
        return THEME_PALETTE[count % len(THEME_PALETTE)]

    def add_theme(self, name: str, color: Optional[str] = None) -> Theme:
        color = color or self.next_theme_color()
        cur = self._conn.execute(
            "INSERT INTO themes (name, color) VALUES (?, ?)", (name.strip(), color)
        )
        self._conn.commit()
        return Theme(id=cur.lastrowid, name=name.strip(), color=color)

    def rename_theme(self, theme_id: int, new_name: str):
        self._conn.execute(
            "UPDATE themes SET name = ? WHERE id = ?", (new_name.strip(), theme_id)
        )
        self._conn.commit()

    def set_theme_color(self, theme_id: int, color: str):
        self._conn.execute("UPDATE themes SET color = ? WHERE id = ?", (color, theme_id))
        self._conn.commit()

    def delete_theme(self, theme_id: int):
        self._conn.execute("DELETE FROM themes WHERE id = ?", (theme_id,))
        self._conn.commit()

    def get_or_create_theme(self, name: str) -> Theme:
        row = self._conn.execute(
            "SELECT * FROM themes WHERE name = ?", (name.strip(),)
        ).fetchone()
        if row:
            return Theme(id=row["id"], name=row["name"], color=row["color"])
        return self.add_theme(name)

    # ---------- Questions ----------

    def list_questions(self, theme_id: int) -> List[Question]:
        rows = self._conn.execute(
            "SELECT * FROM questions WHERE theme_id = ? ORDER BY id", (theme_id,)
        ).fetchall()
        return [
            Question(id=r["id"], theme_id=r["theme_id"], question=r["question"], answer=r["answer"])
            for r in rows
        ]

    def count_questions(self, theme_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM questions WHERE theme_id = ?", (theme_id,)
        ).fetchone()
        return row["c"]

    def add_question(self, theme_id: int, question: str, answer: str) -> Question:
        cur = self._conn.execute(
            "INSERT INTO questions (theme_id, question, answer) VALUES (?, ?, ?)",
            (theme_id, question.strip(), answer.strip()),
        )
        self._conn.commit()
        return Question(id=cur.lastrowid, theme_id=theme_id, question=question.strip(), answer=answer.strip())

    def update_question(self, question_id: int, question: str, answer: str):
        self._conn.execute(
            "UPDATE questions SET question = ?, answer = ? WHERE id = ?",
            (question.strip(), answer.strip(), question_id),
        )
        self._conn.commit()

    def delete_question(self, question_id: int):
        self._conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        self._conn.commit()

    def bulk_add_questions(self, theme_id: int, pairs: List[tuple]) -> int:
        count = 0
        for question, answer in pairs:
            question = (question or "").strip()
            answer = (answer or "").strip()
            if not question or not answer:
                continue
            self._conn.execute(
                "INSERT INTO questions (theme_id, question, answer) VALUES (?, ?, ?)",
                (theme_id, question, answer),
            )
            count += 1
        self._conn.commit()
        return count

    # ---------- Settings ----------

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return row["value"]

    def set_setting(self, key: str, value: str):
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        self._conn.commit()

    # ---------- Saved game ----------

    def save_game(self, data: dict):
        self.set_setting("saved_game", json.dumps(data))

    def load_game(self) -> Optional[dict]:
        raw = self.get_setting("saved_game", "")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return None

    def clear_saved_game(self):
        self.set_setting("saved_game", "")

    # ---------- Maintenance ----------

    def close(self):
        self._conn.close()

    def reset_question_bank(self):
        self._conn.execute("DELETE FROM questions")
        self._conn.execute("DELETE FROM themes")
        self._conn.commit()
        self.clear_saved_game()

    def next_player_color(self, index: int) -> str:
        return PLAYER_PALETTE[index % len(PLAYER_PALETTE)]
