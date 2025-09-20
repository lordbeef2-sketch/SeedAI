from fastapi import APIRouter, HTTPException
import os, json, time

router = APIRouter(prefix="/api", tags=["openwebui-compat"])

def _ollama_base():
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    if base.lower().endswith("/v1"):
        base = base[:-3]
    return base

def _get(url: str, timeout: float = 5.0):
    try:
        import httpx
        r = httpx.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        pass
    try:
        import requests
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        pass
    from urllib.request import urlopen
    with urlopen(url, timeout=timeout) as f:
        return json.loads(f.read().decode("utf-8"))

@router.get("/models")
def list_models():
    base = _ollama_base()
    url = f"{base}/api/tags"
    try:
        data = _get(url, timeout=5.0)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model probe failed: {e}")

    models = []
    for m in data.get("models", []):
        mid = m.get("name") or m.get("model") or "unknown"
        models.append({
            "id": mid,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "ollama",
        })
    return {"object": "list", "data": models}
