from fastapi import APIRouter, Request, HTTPException
from gateway.seedai_storage import load_core, save_core, list_conversations, load_conversation, get_memory_summary

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
        return list_conversations()
    except Exception:
        return []


@router.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    try:
        return load_conversation(conversation_id)
    except Exception:
        return {}


@router.get("/api/memory/summary")
async def memory_summary(limit: int = 5):
    try:
        return get_memory_summary(limit=limit)
    except Exception:
        return {"total": 0, "recent": [], "topic_counts": {}}
