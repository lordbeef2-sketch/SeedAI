import os
from fastapi import HTTPException, Request


def _is_dev_auth_enabled() -> bool:
    return os.environ.get("DEV_AUTH", "false").lower() in ("1", "true", "yes")


def require_auth(request: Request):
    """Require a Bearer token in Authorization header unless DEV_AUTH is enabled.

    This function reads the `Authorization` header directly to avoid FastAPI's
    HTTPBearer dependency which would automatically return 403 before we can
    check `DEV_AUTH`.
    """
    if _is_dev_auth_enabled():
        return {"dev": True}

    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    api_key = os.getenv("GATEWAY_API_KEY", "changeme")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = auth.split(None, 1)[1].strip()
    if token != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"api_key": token}


def ip_allowlist(request: Request):
    if _is_dev_auth_enabled():
        return request
    client_ip = request.client.host
    allowed_ips = [ip.strip() for ip in os.getenv("ALLOWED_IPS", "127.0.0.1,::1").split(",")]
    if client_ip not in allowed_ips:
        raise HTTPException(status_code=403, detail="IP not allowed")
    return request