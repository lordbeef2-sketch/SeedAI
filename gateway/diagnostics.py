from fastapi import APIRouter
from pathlib import Path
from datetime import datetime
import json, os

router = APIRouter(prefix="/diag", tags=["diagnostics"])

def _core_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    memdir = root / "memory"
    memdir.mkdir(parents=True, exist_ok=True)
    return memdir / "core.json"

def _load_core() -> dict:
    p = _core_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "meta": {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_boot": datetime.utcnow().isoformat() + "Z",
            "note": "Seed memory file for Aurelia",
        },
        "user": {"display_name": "Lord Shinza", "role": "Owner/Co-parent"},
        "ai": {
            "name": "Aurelia",
            "codename": "SeedAI",
            "persona": "Emotionally intelligent, kind, helpful, learning-first",
            "principles": [
                "Be truthful and kind",
                "Prefer memory-first recall before LLM",
                "Ask before crawling or using external sources",
            ],
        },
        "settings": {"persistence_enabled": True, "memory_file_format": "json"},
        "memory": {"facts": [], "feelings": [], "vocab": [], "imprint": [], "events": []},
    }

def _atomic_write(path: Path, data: dict):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

@router.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}

@router.post("/memory/test-write")
def test_write(note: str | None = None):
    core_path = _core_path()
    data = _load_core()
    data.setdefault("memory", {}).setdefault("events", [])
    evt = {
        "type": "test-write",
        "ts": datetime.utcnow().isoformat() + "Z",
        "note": note or "hello from /diag/memory/test-write",
    }
    data["memory"]["events"].append(evt)
    data.setdefault("meta", {})["last_boot"] = datetime.utcnow().isoformat() + "Z"
    _atomic_write(core_path, data)
    return {"ok": True, "wrote": evt, "core_json": str(core_path), "events_count": len(data["memory"]["events"])}
