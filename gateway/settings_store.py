import os
import json
import sqlite3
from typing import Dict, Any

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'memory', 'settings.db')

def _ensure_db():
    d = os.path.dirname(_DB_PATH)
    os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()


def get_all_settings() -> Dict[str, Any]:
    _ensure_db()
    conn = sqlite3.connect(_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    conn.close()
    out: Dict[str, Any] = {}
    for k, v in rows:
        try:
            out[k] = json.loads(v)
        except Exception:
            out[k] = v
    return out


def save_settings(settings: Dict[str, Any]):
    _ensure_db()
    conn = sqlite3.connect(_DB_PATH)
    cur = conn.cursor()
    for k, v in settings.items():
        try:
            sval = json.dumps(v)
        except Exception:
            sval = str(v)
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, sval))
    conn.commit()
    conn.close()
