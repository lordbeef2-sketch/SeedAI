# gateway/core_store.py
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict

CORE_BLOCK_RE = re.compile(
    r"CORE\s+MEMORY\s+UPDATE\s*(\{.*?\})\s*END_CORE_MEMORY_UPDATE",
    re.IGNORECASE | re.DOTALL,
)

def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("{}", encoding="utf-8")

def _load_json(p: Path) -> Dict[str, Any]:
    _ensure_parent(p)
    try:
        return json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}

def _dump_json(p: Path, data: Dict[str, Any]) -> None:
    _ensure_parent(p)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst

def merge_into_core(core_path: Path, payload: Dict[str, Any], namespace: str = "aurelia") -> Dict[str, Any]:
    data = _load_json(core_path)
    if namespace not in data or not isinstance(data.get(namespace), dict):
        data[namespace] = {}
    deep_merge(data[namespace], payload)
    _dump_json(core_path, data)
    return data

def parse_core_block(text: str) -> Dict[str, Any] | None:
    m = CORE_BLOCK_RE.search(text or "")
    if not m:
        return None
    raw = m.group(1)
    try:
        return json.loads(raw)
    except Exception:
        return None
