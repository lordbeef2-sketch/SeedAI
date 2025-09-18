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


@router.get("/api/conversations")
async def get_conversations():
    try:
        from gateway.core_memory_handler import load_all_conversations
        return load_all_conversations()
    except Exception:
        return {}


@router.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    try:
        from gateway.core_memory_handler import load_all_conversations
        allc = load_all_conversations()
        return allc.get(conversation_id, {})
    except Exception:
        return {}
