# gateway/openwebui_models_probe.py
from fastapi import APIRouter
import urllib.request, json

router = APIRouter()
OLLAMA_BASE = "http://127.0.0.1:11434"

@router.get("/api/models")
def models_probe():
    candidates = ("/v1/models", "/models", "/api/tags", "/v1/tags")
    last_err = None
    for p in candidates:
        url = OLLAMA_BASE.rstrip("/") + p
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"AureliaProbe/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict) and "models" in data:
                        names = [m.get("name") if isinstance(m, dict) else str(m) for m in data["models"]]
                    elif isinstance(data, list):
                        names = [ (item.get("name") if isinstance(item, dict) else str(item)) for item in data ]
                    else:
                        names = [w for w in raw.split() if any(t in w.lower() for t in ("llama","gemma","mistral","qwen"))]
                    return {"ok": True, "endpoint": p, "models": names}
                except Exception:
                    return {"ok": True, "endpoint": p, "raw": raw[:2000]}
        except Exception as e:
            last_err = str(e)
    return {"ok": False, "error": "no ollama endpoint reachable", "last": last_err}