from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..security.auth import require_auth, ip_allowlist

# Import your Reasoner directly
try:
    from SeedAI.seedai_reasoner import Reasoner
except Exception:
    # if package layout differs, adjust this import
    from seedai_reasoner import Reasoner  # fallback

router = APIRouter()

# Singleton Reasoner instance (thread-safe enough for single-process dev)
_reasoner = None
def _get_reasoner():
    global _reasoner
    if _reasoner is None:
        _reasoner = Reasoner()
    return _reasoner

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = "seedai"
    messages: List[Message]
    metadata: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024

@router.post("/v1/chat/completions", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def chat(req: ChatRequest):
    # Accept any "seedai*" model id; treat "seedai" as the program
    if not (req.model or "").startswith("seedai"):
        raise HTTPException(status_code=400, detail="Unsupported model; use 'seedai'")

    user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    if not user_msg:
        raise HTTPException(status_code=400, detail="No user message provided")

    reasoner = _get_reasoner()
    # If your Reasoner needs thread scoping, plumb req.metadata.get("thread_id")
    # and map it to conversation_id internally here.
    meta = {"allow_llm": True, "thread_id": req.metadata.get("thread_id", "api_session") if req.metadata else "api_session"}

    try:
        answer = reasoner.reflect_on_input(user_msg) or ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reasoner error: {e}")

    # OpenAI-compatible response
    return {
        "id": "seedai-chat",
        "object": "chat.completion",
        "created": 0,
        "model": req.model or "seedai",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }