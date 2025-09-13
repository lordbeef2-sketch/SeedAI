import os
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = os.getenv("GATEWAY_API_KEY", "changeme")
    if credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials

def ip_allowlist(request: Request):
    client_ip = request.client.host
    allowed_ips = os.getenv("ALLOWED_IPS", "127.0.0.1,::1").split(",")
    if client_ip not in allowed_ips:
        raise HTTPException(status_code=403, detail="IP not allowed")
    return request