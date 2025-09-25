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


@router.post('/api/persona/save', dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def api_save_persona(body: dict):
    try:
        persona_text = body.get('persona')
        if persona_text is None:
            raise HTTPException(status_code=400, detail='missing "persona" in request body')

        import os
        from datetime import datetime

        persona_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'seedai', 'persona_aurelia.md')
        # Normalize the path because the join above may contain .. segments
        persona_path = os.path.normpath(persona_path)

        # Make a timestamped backup of existing persona if present
        if os.path.exists(persona_path):
            backup_path = persona_path + '.' + datetime.utcnow().strftime('%Y%m%d%H%M%S') + '.bak'
            try:
                with open(persona_path, 'r', encoding='utf-8') as f:
                    old = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(old)
            except Exception:
                # non-fatal: continue and still attempt to write new persona
                backup_path = None
        else:
            backup_path = None

        # Write new persona
        with open(persona_path, 'w', encoding='utf-8') as f:
            written = f.write(persona_text)

        return {
            'ok': True,
            'path': persona_path,
            'bytes': written,
            'backup': backup_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
