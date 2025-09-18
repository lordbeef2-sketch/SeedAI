SeedAI Quick Fix Bundle (vision model)
=====================================

Defaults:
- Provider: Ollama (http://127.0.0.1:11434/v1)
- Model: llama3.2-vision:11b

Files:
- tools/progress_report.py            (drop-in reporter; stdlib only)
- gateway/openwebui_models_probe.py   (/api/models shim for Ollama discovery)
- gateway/app.patch.txt               (paste into gateway/app.py)
- provider.json                       (optional drop-in, sets defaults)

Apply:
1) Copy/overwrite files into your repo (same paths).
2) Open gateway/app.py and paste blocks from gateway/app.patch.txt in the indicated places.
3) Start Ollama:   ollama serve    (ensure llama3.2-vision:11b is listed: `ollama list`)
4) Run backend:    $env:PYTHONPATH="." ; uvicorn gateway.app:app --host 0.0.0.0 --port 8090
5) Verify:         http://127.0.0.1:8090/api/models  -> lists llama3.2-vision:11b
6) Reporter:       python -m tools.progress_report
7) Check outputs:  diagnostics/progress_report.md  +  ElysiaDigest/latest/digest.md

Env overrides (optional):
- OLLAMA_BASE_URL=http://127.0.0.1:11434
- AURELIA_DEFAULT_MODEL=llama3.2-vision:11b