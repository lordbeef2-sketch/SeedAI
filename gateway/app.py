from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import threading

app = FastAPI(title="SeedAI Gateway", version="1.0.0")

# CORS for dev
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
try:
    from .routes import models, chat
except ImportError:
    from routes import models, chat
app.include_router(models.router)
app.include_router(chat.router)

@app.get("/healthz")
def healthz():
    return {"ok": True, "version": "1.0.0"}

# Start progress reporter
try:
    import sys
    sys.path.append('../..')
    from tools.progress_report import run_reporter
    threading.Thread(target=run_reporter, daemon=True).start()
except Exception as e:
    print(f"Failed to start progress reporter: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8088"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")