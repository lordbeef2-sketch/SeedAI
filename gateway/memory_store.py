"""Compatibility shim: delegate legacy `memory_store` functions to
`gateway.seedai_storage` which provides the new SQLite-backed implementation.
"""
try:
    from gateway.seedai_storage import load_core, save_core
except Exception:
    # fallback implementations if seedai_storage isn't available
    from pathlib import Path
    import json

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

    def save_core(new_dict: dict):
        core = load_core()
        for k, v in new_dict.items():
            core[k] = v
        CORE_JSON.write_text(json.dumps(core, indent=2, ensure_ascii=False), encoding="utf-8")
        return core
