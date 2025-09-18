"""
seedai_storage.py
SQLite-backed persistence for Aurelia (conversations, messages, memory).
Drop into your backend and import functions shown in integration_example.py.
"""
import sqlite3
import json
import time
import pathlib
import re
from typing import Optional, Dict, Any, List

DB_PATH = pathlib.Path("seedai_store.sqlite3")
CORE_RE = re.compile(r"CORE_MEMORY_UPDATE\s*(\{.*?\})\s*END_CORE_MEMORY_UPDATE", re.DOTALL | re.IGNORECASE)

def init_db(db_path: str = None):
    db = str(db_path or DB_PATH)
    conn = sqlite3.connect(db, timeout=30)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT,
        meta_json TEXT,
        updated_at TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        role TEXT,
        text TEXT,
        ts TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        topic TEXT,
        owner TEXT,
        entry_json TEXT,
        verbatim INTEGER DEFAULT 0,
        ts TEXT
    )""")
    conn.commit()
    conn.close()

def _now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def extract_core_json(text: str) -> Optional[Dict[str,Any]]:
    m = CORE_RE.search(text)
    if not m:
        return None
    try:
        js = json.loads(m.group(1))
        return js
    except Exception as e:
        # parse error - log and ignore
        print("[seedai_storage] CORE parse error:", e)
        return None

def strip_core_blocks(text: str) -> str:
    return CORE_RE.sub("", text).strip()

def save_memory_entry(entry: Dict[str,Any], source: str = "aurelia", verbatim: bool = False):
    topic = entry.get("topic") or entry.get("key") or None
    owner = entry.get("owner") or entry.get("owner_id") or None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO memory (source, topic, owner, entry_json, verbatim, ts) VALUES (?,?,?,?,?,?)",
        (source, topic, owner, json.dumps(entry, ensure_ascii=False), 1 if verbatim else 0, _now_ts())
    )
    conn.commit()
    conn.close()

def forget_memory(topic: str = None, owner: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if topic and owner:
        c.execute("DELETE FROM memory WHERE topic=? AND owner=?", (topic, owner))
    elif topic:
        c.execute("DELETE FROM memory WHERE topic=?", (topic,))
    elif owner:
        c.execute("DELETE FROM memory WHERE owner=?", (owner,))
    else:
        conn.close()
        return
    conn.commit()
    conn.close()

def query_memory_by_topic(topic: str) -> List[Dict[str,Any]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, source, topic, owner, entry_json, verbatim, ts FROM memory WHERE topic=?", (topic,))
    rows = c.fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "source": r[1],
            "topic": r[2],
            "owner": r[3],
            "entry": json.loads(r[4]) if r[4] else None,
            "verbatim": bool(r[5]),
            "ts": r[6]
        })
    return results

def get_memory_summary(limit: int = 5) -> Dict[str,Any]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM memory")
    total = c.fetchone()[0]
    c.execute("SELECT topic, owner, entry_json, ts FROM memory ORDER BY id DESC LIMIT ?", (limit,))
    recent = [{"topic": r[0],"owner": r[1],"entry": json.loads(r[2]), "ts": r[3]} for r in c.fetchall()]
    conn.close()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT topic, COUNT(*) FROM memory GROUP BY topic")
    topic_counts = {r[0]: r[1] for r in c.fetchall() if r[0] is not None}
    conn.close()
    return {"total": total, "recent": recent, "topic_counts": topic_counts}

def append_message(conversation_id: str, role: str, text: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (conversation_id, role, text, ts) VALUES (?,?,?,?)",
              (conversation_id, role, text, _now_ts()))
    c.execute("REPLACE INTO conversations (id, title, meta_json, updated_at) VALUES (?,?,?,?)",
              (conversation_id, None, json.dumps({"id": conversation_id}), _now_ts()))
    conn.commit()
    conn.close()

def load_conversation(conversation_id: str) -> Dict[str,Any]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, meta_json, updated_at FROM conversations WHERE id=?", (conversation_id,))
    conv = c.fetchone()
    if not conv:
        conn.close()
        return {"id": conversation_id, "messages": []}
    c.execute("SELECT role, text, ts FROM messages WHERE conversation_id=? ORDER BY id ASC", (conversation_id,))
    rows = c.fetchall()
    conn.close()
    messages = [{"role": r[0], "text": r[1], "ts": r[2]} for r in rows]
    return {"id": conv[0], "title": conv[1], "meta": json.loads(conv[2]) if conv[2] else None, "updated_at": conv[3], "messages": messages}

def list_conversations() -> List[Dict[str,Any]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]

# Integration helper: process model output
def process_model_output(conversation_id: str, model_text: str, source: str = "aurelia"):
    """
    Call this with the model's raw text output (string).
    - Extract and persist any CORE_MEMORY_UPDATE blocks
    - Strip CORE blocks before returning sanitized_text
    - Append sanitized assistant message to messages table
    Returns: sanitized_text, parsed_core (or None)
    """
    parsed = extract_core_json(model_text)
    if parsed:
        # save memory entry (mark as verbatim if a value key exists)
        save_memory_entry(parsed, source=source, verbatim=1 if parsed.get("value") else 0)
        # log to server/terminal only
        print(f"[seedai_storage] CORE_MEMORY_UPDATE received and saved: {parsed}")
    sanitized = strip_core_blocks(model_text)
    # append assistant message to conversation
    append_message(conversation_id, "assistant", sanitized)
    return sanitized, parsed
