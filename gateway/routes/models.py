from fastapi import APIRouter, Depends
from gateway.security.auth import require_auth, ip_allowlist
import requests

router = APIRouter()

OLLAMA_URL = "http://127.0.0.1:11434"

@router.get("/v1/models", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def list_models():
    try:
        response = requests.get(f"{OLLAMA_URL}/v1/models", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"object": "list", "data": []}
    except Exception:
        return {"object": "list", "data": []}

@router.get("/models", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def list_models_alias():
    return await list_models()