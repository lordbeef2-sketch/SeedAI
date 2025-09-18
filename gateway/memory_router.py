from fastapi import APIRouter, Request, HTTPException
from gateway.memory_store import load_core, save_core

router = APIRouter()


@router.get("/api/memory")
async def get_memory():
    return load_core()


@router.post("/api/memory")
async def post_memory(req: Request):
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")
    saved = save_core(data)
    return {"ok": True, "saved_keys": list(data.keys()), "core": saved}
