from fastapi import APIRouter, Depends, HTTPException
from gateway.security.auth import require_auth, ip_allowlist
from gateway import settings_store

router = APIRouter()


@router.get('/api/settings', dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def api_get_settings():
    try:
        return {'settings': settings_store.get_all_settings()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/api/settings', dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def api_save_settings(body: dict):
    try:
        settings_store.save_settings(body.get('settings') or body)
        return {'ok': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
