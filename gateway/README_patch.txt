SeedAI SQLite persistence patch
===============================

Files included:
- seedai_storage.py       : SQLite persistence helpers and CORE block handling.
- integration_example.py  : FastAPI example showing startup, endpoints, and message handler wiring.
- apply_patch.sh          : small helper to copy files into a repo (optional).

Quick install (manual):
1. Copy seedai_storage.py into your backend (e.g., backend/ or seedai/).
2. Import and call storage.init_db() at server startup (see integration_example.startup()).
3. In your model response pipeline, after getting model_text, call:
     sanitized, parsed_core = storage.process_model_output(conversation_id, model_text, source="aurelia")
   and return sanitized to the frontend.
4. Call storage.append_message(conversation_id, "user", user_text) when receiving user input.
5. Expose endpoints /api/conversations and /api/memory/summary to let the frontend load persisted data.

Migration:
- For small deployments this SQLite DB is robust and transactional.
- If you later want to migrate to a remote DB, export using SELECT * FROM memory/messages.

Notes:
- This patch intentionally strips CORE_MEMORY_UPDATE blocks before returning to the UI and logs the parsed JSON server-side.
- The integration_example is intentionally minimal; adapt to your actual backend framework and model-calling code.
