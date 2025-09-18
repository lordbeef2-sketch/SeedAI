"""
integration_example.py

Example FastAPI integration showing:
- init_db() at startup
- endpoints: /api/conversations, /api/conversations/{id}, /api/memory/summary
- example message handler wiring (simulate model output handling)
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import json
import os
import seedai_storage as storage

app = FastAPI()

@app.on_event("startup")
def startup():
    storage.init_db()
    print("[integration] DB initialized at", storage.DB_PATH)
    summary = storage.get_memory_summary(limit=3)
    print("[integration] Memory summary on startup:", summary)

@app.get("/api/conversations")
def api_list_conversations():
    return JSONResponse(content=storage.list_conversations())

@app.get("/api/conversations/{conv_id}")
def api_get_conversation(conv_id: str):
    return JSONResponse(content=storage.load_conversation(conv_id))

@app.get("/api/memory/summary")
def api_memory_summary():
    return JSONResponse(content=storage.get_memory_summary(limit=10))

@app.post("/api/message/{conv_id}")
async def api_receive_message(conv_id: str, request: Request):
    """
    Example endpoint: receive a user message, call your model, get raw model_text,
    then use storage.process_model_output to persist CORE blocks and strip before returning.
    For demo, this endpoint expects a JSON body: {"user":"...","model_text":"..."}
    """
    body = await request.json()
    user_text = body.get("user","")
    model_text = body.get("model_text","")
    # persist user message
    storage.append_message(conv_id, "user", user_text)
    # process model output
    sanitized, parsed_core = storage.process_model_output(conv_id, model_text, source="aurelia")
    # optional: if parsed_core, return human ack instead of raw JSON
    ack = None
    if parsed_core:
        ack = {"status":"memory_saved","summary": parsed_core}
    return JSONResponse(content={"assistant": sanitized, "memory_ack": ack})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT",8091)))
