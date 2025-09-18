from pathlib import Path
import json, tempfile, os, contextlib

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "seedai" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
CORE_JSON = MEMORY_DIR / "core.json"


def load_core() -> dict:
    if not CORE_JSON.exists():
        return {}
    try:
        return json.loads(CORE_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _atomic_write(path: Path, data: str):
    # write to temp file then replace
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            with contextlib.suppress(Exception):
                os.remove(tmp)


def save_core(new_dict: dict):
    core = load_core()
    # shallow merge for top-level keys; you can extend to deep merge if desired
    for k, v in new_dict.items():
        core[k] = v
    _atomic_write(CORE_JSON, json.dumps(core, indent=2, ensure_ascii=False))
    return core
