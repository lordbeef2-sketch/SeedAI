from fastapi import APIRouter, HTTPException, Request
import os, json, pathlib, urllib.request, re, time

# Use the seedai_storage APIs for memory and conversation persistence
try:
    from gateway.seedai_storage import (
        process_model_output,
        save_memory_entry,
        append_message,
    )
except Exception:
    process_model_output = None
    def save_memory_entry(entry, source='aurelia', verbatim=False):
        return entry
    def append_message(conversation_id, role, text):
        return None

# memory store compatibility shim (uses gateway.memory_store which delegates to seedai_storage)
try:
    from gateway.memory_store import load_core, save_core
except Exception:
    def load_core():
        return {}
    def save_core(d):
        return d

# conversation persistence helper (compat shim)
try:
    from gateway.core_memory_handler import persist_conversation, strip_core_blocks as _strip_core_blocks
except Exception:
    def persist_conversation(conversation_id, conversation_obj):
        return conversation_obj
    def _strip_core_blocks(text):
        return text

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

# Load persona text at import-time is fragile if the file is edited while the
# server is running. We will call `_load_persona()` per-request so changes are
# picked up immediately without restarting the backend.

def _post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_API_KEY}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = r.read().decode("utf-8", errors="ignore")
        try:
            return json.loads(text)
        except Exception:
            print("[Aurelia][_post_json] non-json response")
            return {"text": text}

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

    print(f"[Aurelia][chat] incoming request keys: {list(data.keys())}")

    model = data.get("model") or DEFAULT_MODEL
    messages = data.get("messages") or []

    # Build bootstrap messages: persona system message, then core memory, then digest
    bootstrap = []
    try:
        bootstrap = load_bootstrap_messages() or []
    except Exception:
        bootstrap = []

    # Ensure persona is first: replace or insert persona text as first system message
    # Load persona file on each request so edits take effect immediately.
    persona_msg = {"role": "system", "content": _load_persona()}

    # Merge: persona first, then any bootstrap messages that aren't identical
    merged = [persona_msg]
    persona_text = _load_persona()
    for bm in bootstrap:
        # avoid duplicates with the current persona text
        if bm.get("content") and bm.get("content") != persona_text:
            merged.append(bm)

    messages = merged + messages
    print(f"[Aurelia][chat] merged messages count={len(messages)}; first_system={(messages[0]['content'][:60] + '...') if messages else ''}")

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": int(data.get("max_tokens", 512)),
        "temperature": float(data.get("temperature", 0.7)),
        "top_p": float(data.get("top_p", 1.0)),
    }

    # extract conversation id if provided (optional client-supplied id)
    conv_id = data.get("conversation_id") or data.get("conversationId") or None
    # If no conv_id provided, generate one (timestamp-based)
    if not conv_id:
        conv_id = str(int(time.time() * 1000))

    # Persist incoming user messages (append to conversation storage)
    try:
        # store incoming user messages (all non-assistant messages)
        user_msgs = [m for m in messages if m.get("role") != "assistant"]
        if user_msgs:
            persist_conversation(conv_id, {"messages": user_msgs})
    except Exception:
        pass

    try:
        url = OLLAMA_BASE.rstrip("/") + "/v1/chat/completions"
        print(f"[Aurelia][chat] forwarding to Ollama {url} with model={payload.get('model')}")
        out = _post_json(url, payload)
        print(f"[Aurelia][chat] received response type={type(out)}")

        # Extract assistant content
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

        # Detect CORE_MEMORY_UPDATE JSON block and persist to core memory (server-only log)
        try:
            if process_model_output:
                print(f"[Aurelia][chat] calling process_model_output for conv={conv_id}")
                sanitized, parsed = process_model_output(conv_id, assistant_text, source="aurelia")
                print(f"[Aurelia][chat] process_model_output parsed={bool(parsed)}")
                # process_model_output already appended assistant message and saved memory
                if parsed and isinstance(out, dict):
                    out.setdefault("_server", {})["_memory_saved"] = {"keys": list(parsed.keys())}
            else:
                # fallback: try to parse core JSON and save
                from gateway.core_memory_handler import extract_core_json as _ext, append_memory_file as _app
                parsed = _ext(assistant_text)
                if parsed:
                    _app(parsed, source="aurelia")
                    if isinstance(out, dict):
                        out.setdefault("_server", {})["_memory_saved"] = {"keys": list(parsed.keys())}
                sanitized = assistant_text
                print("[Aurelia][chat] fallback parsed and saved")
        except Exception:
            sanitized = assistant_text

        # Strip the CORE_MEMORY_UPDATE block from the assistant-visible text
        try:
            sanitized = _strip_core_blocks(assistant_text)
        except Exception:
            sanitized = assistant_text
        # avoid embedding backslash-escaped sequences directly inside f-strings
        preview = sanitized[:120].replace('\n', ' ')
        print(f"[Aurelia][chat] sanitized assistant text preview: {preview}")
        # If sanitized differs, replace the assistant message content in the returned payload
        try:
            if isinstance(out, dict) and 'choices' in out and isinstance(out['choices'], list) and len(out['choices']):
                choice = out['choices'][0]
                msg = choice.get('message') or choice
                if isinstance(msg, dict) and msg.get('content'):
                    # Optionally append short confirmation to user-visible text
                    confirm = ''
                    if sanitized != assistant_text:
                        confirm = '\n\n[system: memory saved]'
                    msg['content'] = (sanitized + confirm).strip()
                    # write back
                    if 'message' in choice:
                        choice['message'] = msg
                    else:
                        out['choices'][0] = msg
        except Exception:
            pass

        # If process_model_output handled appending assistant message, we're done.
        # Otherwise, persist assistant message to conversation store.
        try:
            if not process_model_output and conv_id:
                assistant_msg = {'role': 'assistant', 'content': sanitized, 'timestamp': int(time.time())}
                try:
                    from gateway.core_memory_handler import persist_conversation as _persist

                    _persist(conv_id, {'messages': [assistant_msg]})
                    print(f"[Aurelia][chat] persisted assistant message to conv {conv_id} via core_memory_handler")
                except Exception:
                    append_message(conv_id, 'assistant', sanitized)
                    print(f"[Aurelia][chat] appended assistant message to conv {conv_id} via seedai_storage.append_message")

            # ensure client knows the conversation id and memory save meta
            if isinstance(out, dict):
                out.setdefault('_server', {})['conversation_id'] = conv_id
        except Exception:
            pass

        return out
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama forward error: {e}")
