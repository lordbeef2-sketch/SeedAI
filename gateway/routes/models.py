from fastapi import APIRouter, Depends, HTTPException
from gateway.security.auth import require_auth, ip_allowlist
from gateway import providers
import requests

router = APIRouter()


def _normalize_models(resp_json):
    # Normalize different provider shapes into a list of {id, owned_by}
    import ast
    models = []
    def push_from_obj(o):
        if isinstance(o, dict):
            mid = o.get('id') or o.get('name') or o.get('model')
            owned = o.get('owned_by') or o.get('owner') or 'library'
            if mid:
                models.append({'id': str(mid), 'owned_by': owned})
                return True
        return False

    if isinstance(resp_json, dict):
        candidates = []
        if 'models' in resp_json and isinstance(resp_json['models'], list):
            candidates = resp_json['models']
        elif 'data' in resp_json and isinstance(resp_json['data'], list):
            candidates = resp_json['data']
        else:
            # try to find any list value
            for v in resp_json.values():
                if isinstance(v, list):
                    candidates = v
                    break
        for m in candidates:
            if not push_from_obj(m):
                # try to parse python-style dict strings
                if isinstance(m, str):
                    try:
                        parsed = ast.literal_eval(m)
                        if push_from_obj(parsed):
                            continue
                    except Exception:
                        pass
                # fallback: treat as id string
                models.append({'id': str(m), 'owned_by': 'library'})
    elif isinstance(resp_json, list):
        for m in resp_json:
            if not push_from_obj(m):
                if isinstance(m, str):
                    try:
                        parsed = ast.literal_eval(m)
                        if push_from_obj(parsed):
                            continue
                    except Exception:
                        pass
                models.append({'id': str(m), 'owned_by': 'library'})
    return models


@router.get("/api/models", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def api_models():
    base = providers.get_base_url()
    candidates = ["/v1/models", "/models", "/api/tags", "/v1/tags", "/v1/engines"]
    errors = []
    for p in candidates:
        url = base + p
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                try:
                    js = r.json()
                    models = _normalize_models(js)
                    if models:
                        return {"models": models}
                except Exception:
                    # try to parse plain text fallback
                    text = r.text or ""
                    found = [w for w in text.split() if any(t in w.lower() for t in ("llama", "gemma", "mistral", "qwen"))]
                    if found:
                        return {"models": found}
            else:
                errors.append(f"{url} -> {r.status_code}")
        except requests.exceptions.RequestException as e:
            errors.append(str(e))
    # If none found, still return empty list rather than error
    return {"models": []}


@router.get("/models", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def list_models_alias():
    return await api_models()