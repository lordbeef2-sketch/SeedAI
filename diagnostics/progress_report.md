# Aurelia Progress Report
Generated: 2025-09-19T22:28:34.873654 UTC

## System
- Platform: Windows-11-10.0.26100-SP0
- Python: 3.13.5 (C:\ProgramData\anaconda3\python.exe)
- CPU count: 24
- RAM: (install psutil for detailed RAM)
- GPU VRAM: unknown

## Ollama Discovery
- Base: http://127.0.0.1:11434
- Path matched: /v1/models (http 200)
- Models: {"object":"list","data":[{"id":"llama3.2-vision:11b","object":"model","created":1757973005,"owned_by":"library"},{"id":"gemma3:12b","object":"model","created":1757179259,"owned_by":"library"}]}
- Selected model: {"object":"list","data":[{"id":"llama3.2-vision:11b","object":"model","created":1757973005,"owned_by":"library"},{"id":"gemma3:12b","object":"model","created":1757179259,"owned_by":"library"}]}

## Backend Health
- import gateway.app: OK (app loaded)
- /healthz probe: OK (200 {"ok":true,"version":"1.0.0"})
- uvicorn probe: OK

## Chat Probe
- Using model: {"object":"list","data":[{"id":"llama3.2-vision:11b","object":"model","created":1757973005,"owned_by":"library"},{"id":"gemma3:12b","object":"model","created":1757179259,"owned_by":"library"}]} -> FAIL
```
HTTP Error 400: Bad Request
```