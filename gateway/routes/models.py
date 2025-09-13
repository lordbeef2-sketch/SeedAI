from fastapi import APIRouter, Depends
from ..security.auth import require_auth, ip_allowlist
import os, json

router = APIRouter()

def _underlying():
    # try SeedAI config; fallback to blank
    try:
        with open(os.path.join("SeedAI","config","llm_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return (cfg.get("model") or "").strip()
    except Exception:
        return ""

@router.get("/v1/models", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def list_models():
    data = [{"id": "seedai", "object": "model"}]
    name = _underlying()
    if name:
        data.append({"id": f"seedai-{name}", "object": "model"})
    return {"object": "list", "data": data}