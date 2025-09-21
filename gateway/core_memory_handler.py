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

from typing import Optional, Dict, Any
import json
from gateway.seedai_storage import (
    extract_core_json as _extract_core_json,
    strip_core_blocks as _strip_core_blocks,
    save_core,
    save_memory_entry,
    load_core,
    list_conversations,
    load_conversation,
    append_message,
)


def append_memory_file(entry: Dict[str, Any], source: str = "aurelia") -> Dict[str, Any]:
    try:
        # use the richer save_memory_entry
        save_memory_entry(entry, source=source, verbatim=bool(entry.get("value")))
        print(f"[memory] appended from {source}: keys={list(entry.keys())}")
        # also store a merged core snapshot if desired
        try:
            if entry.get("type") == "core" or entry.get("key") == "core":
                return save_core(entry)
        except Exception:
            pass
        return entry
    except Exception as e:
        print("[memory] append failed:", e)
        return entry



def extract_core_json(text: str) -> Optional[Dict[str, Any]]:
    return _extract_core_json(text)


def strip_core_blocks(text: str) -> str:
    return _strip_core_blocks(text)


def load_all_conversations():
    return {c["id"]: load_conversation(c["id"]) for c in list_conversations()}


def persist_conversation(conversation_id: str, conversation_obj: Dict[str, Any]):
    # conversation_obj expected to contain {'messages': [...]}
    if not conversation_id:
        import time

        conversation_id = str(int(time.time() * 1000))
    msgs = conversation_obj.get("messages", [])
    for m in msgs:
        role = m.get("role")
        text = m.get("content") or m.get("text") or json.dumps(m)
        append_message(conversation_id, role, text)
    return load_conversation(conversation_id)
