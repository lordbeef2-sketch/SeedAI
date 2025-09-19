from fastapi import APIRouter
from gateway.seedai_storage import list_conversations, load_conversation, get_memory_summary

router = APIRouter()


@router.get("/api/conversations")
async def api_conversations():
    return list_conversations()


@router.get("/api/conversations/{conversation_id}")
async def api_conversation(conversation_id: str):
    return load_conversation(conversation_id)


@router.get("/api/memory/summary")
async def api_memory_summary(limit: int = 5):
    return get_memory_summary(limit=limit)
