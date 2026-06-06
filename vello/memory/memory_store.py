import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path.home() / ".vello" / "memory.db"


class MemoryStore:
    """SQLite backend for persistent cross-session memory."""

    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                type          TEXT    NOT NULL,
                content       TEXT    NOT NULL,
                context       TEXT,
                importance    REAL    DEFAULT 0.5,
                timestamp     TEXT    NOT NULL,
                last_accessed TEXT,
                access_count  INTEGER DEFAULT 0
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_type ON memories(type)"
        )
        self.conn.commit()

    def insert(self, type_: str, content: str, context: str = None,
               importance: float = 0.5) -> int:
        now = datetime.datetime.now().isoformat()
        cur = self.conn.execute(
            """INSERT INTO memories (type, content, context, importance, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (type_, content, context, importance, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def search(self, query: str, type_: str = None, limit: int = 5):
        q = query.lower()
        if type_:
            return self.conn.execute(
                """SELECT id, type, content, context, importance, timestamp
                   FROM memories WHERE type=?
                     AND (LOWER(content) LIKE ? OR LOWER(context) LIKE ?)
                   ORDER BY importance DESC, timestamp DESC LIMIT ?""",
                (type_, f"%{q}%", f"%{q}%", limit),
            ).fetchall()
        return self.conn.execute(
            """SELECT id, type, content, context, importance, timestamp
               FROM memories
               WHERE LOWER(content) LIKE ? OR LOWER(context) LIKE ?
               ORDER BY importance DESC, timestamp DESC LIMIT ?""",
            (f"%{q}%", f"%{q}%", limit),
        ).fetchall()

    def recent(self, type_: str = None, limit: int = 10):
        if type_:
            return self.conn.execute(
                """SELECT id, type, content, context, importance, timestamp
                   FROM memories WHERE type=?
                   ORDER BY timestamp DESC LIMIT ?""",
                (type_, limit),
            ).fetchall()
        return self.conn.execute(
            """SELECT id, type, content, context, importance, timestamp
               FROM memories ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    def delete(self, memory_id: int):
        self.conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        self.conn.commit()

    def touch(self, memory_id: int):
        now = datetime.datetime.now().isoformat()
        self.conn.execute(
            """UPDATE memories
               SET last_accessed=?, access_count=access_count+1
               WHERE id=?""",
            (now, memory_id),
        )
        self.conn.commit()
