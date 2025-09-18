from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from gateway.security.auth import require_auth, ip_allowlist

# Import your Reasoner directly
try:
    from SeedAI.seedai_reasoner import Reasoner
except Exception:
    try:
        # if package layout differs, adjust this import
        from seedai_reasoner import Reasoner  # fallback
    except ImportError:
        # Try relative import
        import sys
        sys.path.append('../..')
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
    # content can be a string or structured (for vision: list of {type, text/image_url})
    content: Any

class ChatRequest(BaseModel):
    model: Optional[str] = "seedai"
    messages: List[Message]
    metadata: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024

@router.post("/api/chat", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def api_chat(req: ChatRequest):
    # Validate messages present
    if not req.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Force stream to False for compatibility
    stream_flag = False

    # Prepare payload for Ollama / OpenAI-compatible endpoint
    payload = {
        "model": req.model or "",
        "messages": [],
        "stream": stream_flag,
        "max_tokens": req.max_tokens or 256,
        "temperature": req.temperature or 0.7,
    }

    # Normalize messages: allow string or structured content
    for m in req.messages:
        content = m.content
        # If content is structured (list), pass through as-is
        if isinstance(content, list):
            payload['messages'].append({"role": m.role, "content": content})
        else:
            payload['messages'].append({"role": m.role, "content": str(content)})

    # Forward to Ollama
    try:
        from gateway import providers
        base = providers.get_base_url()
        api_key = providers.get_api_key() or ""
        url = base.rstrip('/') + "/v1/chat/completions"
        import requests
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        r = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout when contacting model provider")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Provider error: {e}")

    # Return provider's JSON or a normalized error
    try:
        if r.status_code >= 200 and r.status_code < 300:
            return r.json()
        else:
            # Attempt to return provider message
            try:
                err = r.json()
            except Exception:
                err = {"status_code": r.status_code, "text": r.text[:1000]}
            raise HTTPException(status_code=400, detail={"error": "provider_error", "provider": err})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post("/chat/completions", dependencies=[Depends(require_auth), Depends(ip_allowlist)])
async def chat_completions_alias(req: ChatRequest):
    return await api_chat(req)