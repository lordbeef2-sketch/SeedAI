from __future__ import annotations
import os, sqlite3, threading, time
from typing import List, Optional, Tuple, Iterable

DEFAULT_DB = os.path.abspath(os.path.join(os.getcwd(), "data", "aurelia_memory.db"))

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS identity (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS relationships (
  id INTEGER PRIMARY KEY,
  type TEXT,
  target TEXT,
  details TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS capabilities (
  id INTEGER PRIMARY KEY,
  name TEXT,
  description TEXT,
  learned_on DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS principles (
  id INTEGER PRIMARY KEY,
  text TEXT,
  source TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vocab (
  word TEXT PRIMARY KEY,
  definition TEXT,
  examples TEXT,
  learned_on DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS unknown_words (
  word TEXT PRIMARY KEY,
  context TEXT,
  first_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Conversational memory (short & long term)
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY,
  who TEXT,               -- 'user' | 'assistant' | 'system'
  text TEXT,
  meta TEXT,
  ts DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts);

CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY,
  subject TEXT,           -- e.g., 'user', 'aurelia', 'project'
  fact TEXT UNIQUE,
  strength REAL DEFAULT 1.0,
  last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

class Memory:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ---------- low-level ----------
    def _exec(self, sql: str, args: Iterable = ()):
        with self._lock:
            cur = self._conn.execute(sql, args)
            self._conn.commit()
            return cur

    # ---------- messages ----------
    def add_message(self, who: str, text: str, meta: str = "") -> int:
        cur = self._exec(
            "INSERT INTO messages (who, text, meta) VALUES (?,?,?)",
            (who, text, meta),
        )
        return cur.lastrowid

    def recent_messages(self, limit: int = 20) -> List[Tuple[str, str, str, str]]:
        cur = self._exec(
            "SELECT who, text, meta, ts FROM messages ORDER BY ts DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [(r["who"], r["text"], r["meta"], r["ts"]) for r in rows][::-1]

    # ---------- facts ----------
    def upsert_fact(self, subject: str, fact: str, strength: float = 1.0) -> int:
        # strengthen existing fact
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, strength FROM facts WHERE fact = ?", (fact,)
            )
            row = cur.fetchone()
            if row:
                new_strength = min(10.0, row["strength"] + strength)
                self._conn.execute(
                    "UPDATE facts SET subject=?, strength=?, last_seen=CURRENT_TIMESTAMP WHERE id=?",
                    (subject, new_strength, row["id"]),
                )
                self._conn.commit()
                return row["id"]
            cur = self._conn.execute(
                "INSERT INTO facts (subject, fact, strength) VALUES (?,?,?)",
                (subject, fact, strength),
            )
            self._conn.commit()
            return cur.lastrowid

    def recall_facts(self, subject: Optional[str] = None, limit: int = 20) -> List[str]:
        if subject:
            cur = self._exec(
                "SELECT fact FROM facts WHERE subject=? ORDER BY strength DESC, last_seen DESC LIMIT ?",
                (subject, limit),
            )
        else:
            cur = self._exec(
                "SELECT fact FROM facts ORDER BY strength DESC, last_seen DESC LIMIT ?",
                (limit,),
            )
        return [r["fact"] for r in cur.fetchall()]

    # ---------- identity & vocab (helpers) ----------
    def set_identity(self, key: str, value: str):
        self._exec(
            "INSERT INTO identity(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def get_identity(self, key: str) -> Optional[str]:
        cur = self._exec("SELECT value FROM identity WHERE key=?", (key,))
        r = cur.fetchone()
        return r["value"] if r else None

    def add_unknown_word(self, word: str, context: str = ""):
        try:
            self._exec(
                "INSERT INTO unknown_words(word, context) VALUES(?, ?) ON CONFLICT(word) DO NOTHING",
                (word, context),
            )
        except sqlite3.OperationalError:
            # sqlite before 3.24.0 has no DO NOTHING; fallback
            try:
                self._exec("INSERT OR IGNORE INTO unknown_words(word, context) VALUES(?,?)", (word, context))
            except Exception:
                pass

    def close(self):
        with self._lock:
            self._conn.commit()
            self._conn.close()

# ------- tiny diagnostic (run this file directly) -------
if __name__ == "__main__":
    m = Memory()
    print("DB:", m.db_path)
    m.add_message("assistant", "Hello (diagnostic)")
    m.upsert_fact("user", "User likes colorful UIs", strength=0.5)
    print("Recent messages:", m.recent_messages(3))
    print("Top facts:", m.recall_facts(limit=5))
    print("OK.")
