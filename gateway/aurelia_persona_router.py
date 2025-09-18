from fastapi import APIRouter, HTTPException, Request
import os, json, pathlib, urllib.request, re

# memory store
try:
    from gateway.memory_store import load_core, save_core
except Exception:
    def load_core():
        return {}
    def save_core(d):
        return d

# Import bootstrap loader
try:
    from gateway.memory_bootstrap import load_bootstrap_messages
except Exception:
    # fallback: define a noop loader
    def load_bootstrap_messages():
        return []

router = APIRouter()

# Config with env overrides
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "ollama")
DEFAULT_MODEL = os.environ.get("AURELIA_DEFAULT_MODEL", "llama3.2-vision:11b")
PERSONA_PATH = os.environ.get("AURELIA_PERSONA_PATH", "seedai/persona_aurelia.md")

def _load_persona() -> str:
    p = pathlib.Path(PERSONA_PATH)
    if p.exists():
        try:
            return p.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return "You are Aurelia, the SeedAI assistant. Be warm, concise, and helpful."

PERSONA_TEXT = _load_persona()

def _post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_API_KEY}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="ignore"))

@router.post("/api/chat")
async def chat_with_persona(req: Request):
    """
    OpenAI-compatible chat endpoint that injects Aurelia persona as a system message,
    then forwards to Ollama /v1/chat/completions.
    """
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = data.get("model") or DEFAULT_MODEL
    messages = data.get("messages") or []

    # Build bootstrap messages: persona system message, then core memory, then digest
    bootstrap = []
    try:
        bootstrap = load_bootstrap_messages() or []
    except Exception:
        bootstrap = []

    # Ensure persona is first: replace or insert persona text as first system message
    persona_msg = {"role": "system", "content": PERSONA_TEXT}

    # Merge: persona first, then any bootstrap messages that aren't identical
    merged = [persona_msg]
    for bm in bootstrap:
        # avoid duplicates
        if bm.get("content") and bm.get("content") != PERSONA_TEXT:
            merged.append(bm)

    messages = merged + messages

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": int(data.get("max_tokens", 512)),
        "temperature": float(data.get("temperature", 0.7)),
        "top_p": float(data.get("top_p", 1.0)),
    }

    try:
        url = OLLAMA_BASE.rstrip("/") + "/v1/chat/completions"
        out = _post_json(url, payload)

        # Inspect assistant text for CORE_MEMORY_UPDATE block and persist
        assistant_text = ""
        try:
            if isinstance(out, dict):
                ch = out.get("choices")
                if ch and isinstance(ch, list) and len(ch):
                    msg = ch[0].get("message") or ch[0]
                    assistant_text = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                else:
                    assistant_text = out.get("text") or str(out)
            else:
                assistant_text = str(out)
        except Exception:
            assistant_text = str(out)

        m = re.search(r"CORE_MEMORY_UPDATE\s*\n(\{[\s\S]*?\})\s*\nEND_CORE_MEMORY_UPDATE", assistant_text)
        if m:
            try:
                upd_json = json.loads(m.group(1))
                saved = save_core(upd_json)
                if isinstance(out, dict):
                    out.setdefault("_server", {})["_memory_saved"] = {"keys": list(upd_json.keys())}
            except Exception:
                # ignore save errors
                pass

        return out
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama forward error: {e}")
