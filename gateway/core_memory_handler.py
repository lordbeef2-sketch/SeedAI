"""Helper for CORE_MEMORY_UPDATE handling and conversation persistence.

Functions:
- extract_core_json(text: str) -> dict | None
- strip_core_blocks(text: str) -> str
- append_memory_file(entry: dict, source="aurelia") -> dict (saved core)
- persist_conversation(conversation_id: str, conversation_obj: dict) -> dict
- load_all_conversations() -> dict

Persistence files (under seedai/memory):
- core.json (merged core memory) -- via gateway.memory_store.save_core
- conversations.json (all conversations)
"""

from pathlib import Path
import json
import re
import time
import tempfile
import os
import contextlib
from typing import Optional, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "seedai" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_FILE = MEMORY_DIR / "conversations.json"

# Regex to find CORE_MEMORY_UPDATE blocks
_CORE_RE = re.compile(r"CORE_MEMORY_UPDATE\s*\n(\{[\s\S]*?\})\s*\nEND_CORE_MEMORY_UPDATE", re.MULTILINE)


def _atomic_write(path: Path, data: str):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            with contextlib.suppress(Exception):
                os.remove(tmp)


def extract_core_json(text: str) -> Optional[Dict[str, Any]]:
    """Return parsed JSON dict from CORE_MEMORY_UPDATE block if present, else None."""
    if not text:
        return None
    m = _CORE_RE.search(text)
    if not m:
        return None
    raw = m.group(1)
    try:
        parsed = json.loads(raw)
        return parsed
    except Exception:
        return None


def strip_core_blocks(text: str) -> str:
    """Return text with CORE_MEMORY_UPDATE blocks removed."""
    if not text:
        return text
    return _CORE_RE.sub("", text).strip()


def append_memory_file(entry: Dict[str, Any], source: str = "aurelia") -> Dict[str, Any]:
    """Append/merge an entry into core memory using existing memory_store if available.

    Returns the saved core dict.
    """
    # Prefer to use gateway.memory_store.save_core if available
    try:
        from gateway.memory_store import save_core

        # Save shallow merge via save_core
        saved = save_core(entry)
        # Also print server-only log of raw block (do not return to client)
        print(f"[memory] appended from {source}: keys={list(entry.keys())}")
        return saved
    except Exception:
        # Fallback: write to core.json directly
        core_path = MEMORY_DIR / "core.json"
        core = {}
        if core_path.exists():
            try:
                core = json.loads(core_path.read_text(encoding="utf-8"))
            except Exception:
                core = {}
        core.update(entry)
        _atomic_write(core_path, json.dumps(core, indent=2, ensure_ascii=False))
        print(f"[memory] appended (fallback) from {source}: keys={list(entry.keys())}")
        return core


def _load_conversations() -> Dict[str, Any]:
    if not CONVERSATIONS_FILE.exists():
        return {}
    try:
        return json.loads(CONVERSATIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_all_conversations() -> Dict[str, Any]:
    return _load_conversations()


def persist_conversation(conversation_id: str, conversation_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Persist conversation (shallow replace/merge) and return saved object."""
    if not conversation_id:
        # generate a weak id
        conversation_id = str(int(time.time() * 1000))
    allc = _load_conversations()
    # Merge or replace conversation entry
    existing = allc.get(conversation_id, {})
    # we'll store fields: id, messages (list), updated
    msgs = existing.get("messages", [])
    new_msgs = conversation_obj.get("messages", [])
    # naive append new messages (assume caller supplies only the delta or full state)
    if new_msgs:
        # if last message id matches, avoid duplicate; simple heuristic
        msgs.extend(new_msgs)
    else:
        msgs = msgs

    saved = {
        "id": conversation_id,
        "messages": msgs,
        "updated": int(time.time()),
    }
    allc[conversation_id] = saved
    _atomic_write(CONVERSATIONS_FILE, json.dumps(allc, indent=2, ensure_ascii=False))
    return saved
