# Define BASE_OLLAMA for the application
BASE_OLLAMA = "http://127.0.0.1:11434"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import threading
import sys

# Ensure the project root is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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

# Dev-friendly CORS (restrict in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# optional: only if you created the reporter and router files
try:
    from gateway.openwebui_models_probe import router as probe_router
except Exception:
    probe_router = None

if probe_router is not None:
    app.include_router(probe_router)

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

# non-blocking reporter run (optional; safe guard)
try:
    import threading
    def _start_reporter():
        try:
            from tools.progress_report import main as _progress_main
            _progress_main()
        except Exception:
            pass
    threading.Thread(target=_start_reporter, daemon=True).start()
except Exception:
    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8090"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")