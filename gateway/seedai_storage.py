"""seedai_storage.py
Enhanced SQLite-backed persistence for Aurelia (memories, vocab, emotions,
reflections, conversations and messages). This module preserves the older
in-process API (load_core/save_core, append_message, list_conversations,
load_conversation, process_model_output) so existing code continues to work,
while providing a richer schema, indexes, migration and export utilities.

Key features:
- Separate tables for different memory types (memories, vocab, emotions,
  reflections) while keeping a 'core' memory entry compatible with previous
  API.
- Fast read/write with indexes for topic/word/timestamp lookups.
- Migration function from a legacy JSON memory folder.
- `export_memory_json` for human-readable backups.
- `init_db` / `close_db` for startup/shutdown lifecycle management.
"""

import sqlite3
import json
import time
import pathlib
import re
from typing import Optional, Dict, Any, List
from memory_manager import MemoryManager

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_DB_DIR = ROOT / "seedai" / "memory"
DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DEFAULT_DB_DIR / "seedai_store.sqlite3"

CORE_RE = re.compile(r"CORE_MEMORY_UPDATE\s*(\{.*?\})\s*END_CORE_MEMORY_UPDATE", re.DOTALL | re.IGNORECASE)

# module-level connection (opened by init_db)
_conn: Optional[sqlite3.Connection] = None
# MemoryManager instance (optional)
_mm: Optional[MemoryManager] = None


def _now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        # fallback to a short-lived connection
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def init_db(db_path: Optional[str] = None):
    """Initialize the DB and keep a persistent connection for the process.

    Call from FastAPI startup to ensure DB is ready.
    """
    global DB_PATH, _conn
    if db_path:
        DB_PATH = pathlib.Path(db_path)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    global _mm, _conn
    # prefer MemoryManager-backed connection so we share the same DB and
    # benefit from its performance pragmas and schema management
    try:
        _mm = MemoryManager(db_path=str(DB_PATH))
        _conn = _mm._conn
    except Exception:
        # fallback to direct sqlite connection
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    c = _conn.cursor()

    # memories: store different memory types; keep a canonical core memory with
    # type='core' and key='core' to preserve legacy load_core/save_core API.
    c.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        key TEXT,
        topic TEXT,
        owner TEXT,
        data_json TEXT,
        ts TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_memories_type_key ON memories(type, key)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_memories_topic ON memories(topic)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_memories_owner ON memories(owner)")

    # vocab
    c.execute("""
    CREATE TABLE IF NOT EXISTS vocab (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT,
        meaning_json TEXT,
        ts TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocab(word)")

    # emotions
    c.execute("""
    CREATE TABLE IF NOT EXISTS emotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag TEXT,
        data_json TEXT,
        ts TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_emotions_tag ON emotions(tag)")

    # reflections / notes
    c.execute("""
    CREATE TABLE IF NOT EXISTS reflections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        body TEXT,
        ts TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_reflections_ts ON reflections(ts)")

    # conversations / messages (existing API)
    c.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT,
        meta_json TEXT,
        updated_at TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at)")
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        role TEXT,
        text TEXT,
        ts TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_ts ON messages(conversation_id, ts)")

    _conn.commit()


def close_db():
    global _conn
    global _conn, _mm
    if _mm:
        try:
            _mm.close()
        except Exception:
            pass
        _mm = None
        _conn = None
        return
    if _conn:
        try:
            _conn.commit()
            _conn.close()
        except Exception:
            pass
        _conn = None


def extract_core_json(text: str) -> Optional[Dict[str, Any]]:
    m = CORE_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception as e:
        print("[seedai_storage] CORE parse error:", e)
        return None


def strip_core_blocks(text: str) -> str:
    return CORE_RE.sub("", text).strip()


def save_memory_entry(entry: Dict[str, Any], source: str = "aurelia", verbatim: bool = False):
    """Save a memory entry into the appropriate table (default to memories table).

    Entry should be a JSON-serializable dict. We attempt to infer type from
    keys but always save to `memories` table to preserve flexibility.
    """
    conn = get_conn()
    c = conn.cursor()
    topic = entry.get("topic") or entry.get("key") or None
    owner = entry.get("owner") or entry.get("owner_id") or None
    c.execute(
        "INSERT INTO memories (type, key, topic, owner, data_json, ts) VALUES (?,?,?,?,?,?)",
        (entry.get("type") or "generic", entry.get("key") or None, topic, owner, json.dumps(entry, ensure_ascii=False), _now_ts()),
    )
    conn.commit()


def save_core(new_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy-compatible save_core: maintain a canonical 'core' memory entry.

    Performs shallow merge of top-level keys and returns the saved core dict.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT data_json FROM memories WHERE type='core' AND key='core' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    core = {}
    if row and row[0]:
        try:
            core = json.loads(row[0])
        except Exception:
            core = {}
    # shallow merge
    for k, v in new_dict.items():
        core[k] = v

    # upsert: insert new row for core snapshot
    c.execute("INSERT INTO memories (type,key,data_json,ts) VALUES (?,?,?,?)", ("core", "core", json.dumps(core, ensure_ascii=False), _now_ts()))
    conn.commit()
    return core


def load_core() -> Dict[str, Any]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT data_json FROM memories WHERE type='core' AND key='core' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if not row:
        return {}
    try:
        return json.loads(row[0])
    except Exception:
        return {}


def forget_memory(topic: str = None, owner: str = None):
    conn = get_conn()
    c = conn.cursor()
    if topic and owner:
        c.execute("DELETE FROM memories WHERE topic=? AND owner=?", (topic, owner))
    elif topic:
        c.execute("DELETE FROM memories WHERE topic=?", (topic,))
    elif owner:
        c.execute("DELETE FROM memories WHERE owner=?", (owner,))
    else:
        return
    conn.commit()


def query_memory_by_topic(topic: str) -> List[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, type, key, topic, owner, data_json, ts FROM memories WHERE topic=? ORDER BY id DESC", (topic,))
    rows = c.fetchall()
    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "type": r[1],
            "key": r[2],
            "topic": r[3],
            "owner": r[4],
            "entry": json.loads(r[5]) if r[5] else None,
            "ts": r[6],
        })
    return results


def get_memory_summary(limit: int = 5) -> Dict[str, Any]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM memories")
    total = c.fetchone()[0]
    c.execute("SELECT topic, owner, data_json, ts FROM memories ORDER BY id DESC LIMIT ?", (limit,))
    recent = [{"topic": r[0], "owner": r[1], "entry": json.loads(r[2]) if r[2] else None, "ts": r[3]} for r in c.fetchall()]
    c.execute("SELECT topic, COUNT(*) FROM memories GROUP BY topic")
    topic_counts = {r[0]: r[1] for r in c.fetchall() if r[0] is not None}
    return {"total": total, "recent": recent, "topic_counts": topic_counts}


def append_message(conversation_id: str, role: str, text: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO messages (conversation_id, role, text, ts) VALUES (?,?,?,?)", (conversation_id, role, text, _now_ts()))
    c.execute("REPLACE INTO conversations (id, title, meta_json, updated_at) VALUES (?,?,?,?)", (conversation_id, None, json.dumps({"id": conversation_id}), _now_ts()))
    conn.commit()


def load_conversation(conversation_id: str) -> Dict[str, Any]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, title, meta_json, updated_at FROM conversations WHERE id=?", (conversation_id,))
    conv = c.fetchone()
    if not conv:
        return {"id": conversation_id, "messages": []}
    c.execute("SELECT role, text, ts FROM messages WHERE conversation_id=? ORDER BY id ASC", (conversation_id,))
    rows = c.fetchall()
    messages = [{"role": r[0], "text": r[1], "ts": r[2]} for r in rows]
    return {"id": conv[0], "title": conv[1], "meta": json.loads(conv[2]) if conv[2] else None, "updated_at": conv[3], "messages": messages}


def list_conversations() -> List[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC")
    rows = c.fetchall()
    return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]


def process_model_output(conversation_id: str, model_text: str, source: str = "aurelia"):
    """Process raw model output: extract and persist CORE blocks, strip them,
    and append the assistant message to the conversation. Returns sanitized_text, parsed_core
    """
    parsed = extract_core_json(model_text)
    if parsed:
        # save memory entry
        save_memory_entry(parsed, source=source, verbatim=bool(parsed.get("value")))
        print(f"[seedai_storage] CORE_MEMORY_UPDATE received and saved: {parsed}")
    sanitized = strip_core_blocks(model_text)
    append_message(conversation_id, "assistant", sanitized)
    return sanitized, parsed


def migrate_from_json(memory_dir: Optional[str] = None):
    """Migrate legacy JSON memory files into SQLite. Accepts path to the
    memory folder (defaults to project `memory` or `seedai/memory`).
    """
    paths_to_try = []
    if memory_dir:
        paths_to_try.append(pathlib.Path(memory_dir))
    # common locations
    paths_to_try.append(ROOT / "memory")
    paths_to_try.append(ROOT / "seedai" / "memory")

    for p in paths_to_try:
        if p and p.exists() and p.is_dir():
            mem_dir = p
            break
    else:
        print("[seedai_storage] No legacy memory directory found for migration")
        return {"migrated": 0}

    migrated = 0
    # migrate core.json
    core_path = mem_dir / "core.json"
    if core_path.exists():
        try:
            # Try reading with utf-8 first; if json decoding fails (common with BOM),
            # retry with utf-8-sig. This covers files that are readable but include
            # a BOM which can cause json.loads to raise a JSONDecodeError.
            core_txt = core_path.read_text(encoding="utf-8")
            try:
                core = json.loads(core_txt)
            except Exception as e_json:
                try:
                    core_txt2 = core_path.read_text(encoding="utf-8-sig")
                    core = json.loads(core_txt2)
                except Exception as e_json2:
                    print(f"[seedai_storage] JSON decode failed for core.json (utf-8 then utf-8-sig): {e_json}; {e_json2}")
                    raise
            save_core(core)
            migrated += 1
            print(f"[seedai_storage] Migrated core.json from {core_path}")
        except Exception as e:
            print("[seedai_storage] Failed to migrate core.json:", e)

    # migrate conversations.json
    conv_path = mem_dir / "conversations.json"
    if conv_path.exists():
        try:
            try:
                convs_txt = conv_path.read_text(encoding="utf-8")
            except Exception:
                convs_txt = conv_path.read_text(encoding="utf-8-sig")
            convs = json.loads(convs_txt)
            for cid, cobj in convs.items():
                # upsert conversation and messages
                c = get_conn().cursor()
                c.execute("REPLACE INTO conversations (id, title, meta_json, updated_at) VALUES (?,?,?,?)", (cid, cobj.get("title"), json.dumps(cobj.get("meta") or {}), _now_ts()))
                msgs = cobj.get("messages", [])
                for m in msgs:
                    c.execute("INSERT INTO messages (conversation_id, role, text, ts) VALUES (?,?,?,?)", (cid, m.get("role"), m.get("content") or m.get("text") or "", _now_ts()))
                get_conn().commit()
            migrated += 1
            print(f"[seedai_storage] Migrated conversations from {conv_path}")
        except Exception as e:
            print("[seedai_storage] Failed to migrate conversations.json:", e)

    # additional files: vocab.json, emotions.json, reflections.json
    for fname, table in [("vocab.json", "vocab"), ("emotions.json", "emotions"), ("reflections.json", "reflections")]:
        fp = mem_dir / fname
        if fp.exists():
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                c = get_conn().cursor()
                if table == "vocab":
                    for w, meaning in data.items():
                        c.execute("INSERT INTO vocab (word, meaning_json, ts) VALUES (?,?,?)", (w, json.dumps(meaning, ensure_ascii=False), _now_ts()))
                elif table == "emotions":
                    for tag, info in data.items():
                        c.execute("INSERT INTO emotions (tag, data_json, ts) VALUES (?,?,?)", (tag, json.dumps(info, ensure_ascii=False), _now_ts()))
                elif table == "reflections":
                    for r in data:
                        c.execute("INSERT INTO reflections (title, body, ts) VALUES (?,?,?)", (r.get("title"), r.get("body"), _now_ts()))
                get_conn().commit()
                migrated += 1
                print(f"[seedai_storage] Migrated {fname}")
            except Exception as e:
                print(f"[seedai_storage] Failed to migrate {fname}:", e)

    return {"migrated": migrated}


def export_memory_json(out_path: Optional[str] = None):
    """Export a human-readable JSON backup of core memory and conversations.

    Returns the exported object and writes to `memory_export.json` by default.
    """
    conn = get_conn()
    c = conn.cursor()
    export = {}
    # core
    core = load_core()
    export["core"] = core
    # recent memories
    c.execute("SELECT id, type, key, topic, owner, data_json, ts FROM memories ORDER BY id DESC LIMIT 200")
    export["memories"] = [{"id": r[0], "type": r[1], "key": r[2], "topic": r[3], "owner": r[4], "entry": json.loads(r[5]) if r[5] else None, "ts": r[6]} for r in c.fetchall()]
    # conversations (limited)
    c.execute("SELECT id FROM conversations ORDER BY updated_at DESC LIMIT 200")
    convs = []
    for r in c.fetchall():
        convs.append(load_conversation(r[0]))
    export["conversations"] = convs

    out_file = pathlib.Path(out_path) if out_path else DEFAULT_DB_DIR / "memory_export.json"
    out_file.write_text(json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8")
    return export

