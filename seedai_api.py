from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from seedai_reasoner import Reasoner
import uvicorn

app = FastAPI(title="SeedAI API", version="1.0.0")

reasoner = Reasoner()

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list
    max_tokens: int = 1000
    temperature: float = 0.7

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list
    usage: dict

class Model(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "seedai"

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "seedai",
                "object": "model",
                "created": 0,
                "owned_by": "seedai"
            }
        ]
    }

@app.get("/models")
async def list_models_alias():
    return await list_models()

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    try:
        # Extract user message
        user_message = ""
        for msg in request.messages:
            if msg["role"] == "user":
                user_message = msg["content"]
                break
        
        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")
        
        # Use SeedAI reasoner
        meta = {"allow_llm": True, "thread_id": "api_session"}
        response_text = reasoner.handle_turn(user_message, meta)
        
        return {
            "id": "chatcmpl-seedai",
            "object": "chat.completion",
            "created": 0,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(user_message.split()) + len(response_text.split())
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/completions")
async def chat_completions_alias(request: ChatCompletionRequest):
    return await chat_completions(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088)