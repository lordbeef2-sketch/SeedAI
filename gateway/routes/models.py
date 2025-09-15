from fastapi import APIRouter, Depends
from gateway.security.auth import require_auth, ip_allowlist
import os, json
from pathlib import Path

router = APIRouter()

def _underlying():
    try:
        here = Path(__file__).resolve()
        repo = here.parents[2]
        cfg_path = repo / "SeedAI" / "config" / "llm_config.json"
        with cfg_path.open("r", encoding="utf-8") as f:
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

@router.get("/models", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def list_models_alias():
    return await list_models()