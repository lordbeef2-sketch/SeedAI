# tools/progress_report.py
"""
Robust progress reporter for Aurelia (SeedAI).

- Writes diagnostics/progress_report.md (full; overwritten each run)
- Appends a concise "## Runtime Check" to ElysiaDigest/latest/digest.md
- Pure stdlib; no GPU/vendor libs
- Non-blocking uvicorn probe (no freezes)
- Ollama chat probe uses OpenAI-compatible JSON with "stream": false
"""

from __future__ import annotations
import os, sys, subprocess, json, platform, time
from pathlib import Path
from datetime import datetime
from typing import Tuple, List

ROOT = Path(__file__).resolve().parents[1]
DIAG_DIR = ROOT / "diagnostics"
DIGEST_DIR = ROOT / "ElysiaDigest" / "latest"
OUT_MD = DIAG_DIR / "progress_report.md"
DIGEST_MD = DIGEST_DIR / "digest.md"

BASE_OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
PREFERRED_MODEL = os.environ.get("AURELIA_DEFAULT_MODEL", "llama3.2-vision:11b")
OLLAMA_PATHS = ("/v1/models", "/models", "/api/tags", "/v1/tags", "/v1/engines")

try:
    from gateway.providers import get_base_url, get_default_model
    try:
        BASE_OLLAMA = get_base_url()
        PREFERRED_MODEL = get_default_model() or PREFERRED_MODEL
    except Exception:
        pass
except Exception:
    # running in environments where gateway isn't importable; ignore
    pass

def _ensure_dirs():
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)

def try_cmd(cmd: list, timeout: int = 10) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout, shell=False)
        return p.returncode, p.stdout.strip()
    except subprocess.TimeoutExpired:
        return 124, f"Timeout after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError as e:
        return 127, f"Not found: {e}"
    except Exception as e:
        return 1, f"Error: {e}"

def http_get(url: str, timeout: int = 5):
    try:
        from urllib.request import urlopen, Request
        req = Request(url, headers={"User-Agent": "Aurelia-Reporter/1.0"})
        with urlopen(req, timeout=timeout) as f:
            return f.getcode(), f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None, str(e)

def discover_ollama_models(base: str):
    last_err = "no endpoint tried"
    for p in OLLAMA_PATHS:
        url = base.rstrip("/") + p
        code, text = http_get(url)
        if code and code < 400:
            try:
                data = json.loads(text)
                if isinstance(data, dict) and "models" in data:
                    names = [m.get("name") if isinstance(m, dict) else str(m) for m in data["models"]]
                elif isinstance(data, list):
                    names = [(x.get("name") if isinstance(x, dict) else str(x)) for x in data]
                else:
                    names = [w for w in text.split() if any(t in w.lower() for t in ("llama", "gemma", "mistral", "qwen"))]
                return p, names, url, code, text
            except Exception:
                return p, [], url, code, text[:2000]
        else:
            last_err = text
    return "", [], "", 0, last_err

def choose_model(models: list) -> str:
    if not models:
        return "none"
    if PREFERRED_MODEL in models:
        return PREFERRED_MODEL
    pref_prefix = PREFERRED_MODEL.split(":", 1)[0]
    for m in models:
        if m.startswith(pref_prefix):
            return m
    return models[0]

def gpu_vram_info() -> str:
    rc, out = try_cmd(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"], timeout=2)
    if rc == 0 and out:
        return f"NVIDIA VRAM (MB): {out}"
    rc, out = try_cmd(["rocm-smi", "--showmeminfo", "vram"], timeout=2)
    if rc == 0 and out:
        return f"ROCm VRAM: {out.splitlines()[0][:200]}"
    return "unknown"

def import_health() -> Tuple[bool, str]:
    try:
        from importlib import import_module
        m = import_module("gateway.app")
        app = getattr(m, "app", None)
        return (app is not None), ("app loaded" if app is not None else "app missing")
    except Exception as e:
        return False, f"import error: {e}"

def fastapi_probe() -> Tuple[bool, str]:
    try:
        from importlib import import_module
        m = import_module("gateway.app")
        app = getattr(m, "app", None)
        if app is None:
            return False, "no app"
        try:
            from fastapi.testclient import TestClient
            with TestClient(app) as c:
                r = c.get("/healthz")
                return (r.status_code == 200), f"{r.status_code} {r.text}"
        except Exception as e:
            return False, f"TestClient error: {e}"
    except Exception as e:
        return False, f"import error: {e}"

def bounded_uvicorn_probe(app_path="gateway.app:app", port=8091, wait_s=3) -> Tuple[bool, str]:
    """
    Start uvicorn in a child proc briefly; don't block on stdout.
    """
    cmd = [sys.executable, "-m", "uvicorn", app_path, "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            # Just wait; do not read stdout synchronously (can block).
            time.sleep(wait_s)
            # Non-blocking collect using communicate with small timeout.
            out, _ = p.communicate(timeout=0.1)
        except Exception:
            out = ""
        finally:
            with contextlib.suppress(Exception):
                p.kill()
        return True, (out or "")[:4000]
    except Exception as e:
        return False, f"uvicorn start error: {e}"

def chat_probe(model: str, base: str) -> Tuple[bool, str]:
    """
    OpenAI-compatible chat completion to Ollama, with stream:false to avoid 400s.
    """
    url = base.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello Aurelia"}],
        "stream": False,
        "max_tokens": 64
    }
    try:
        body = json.dumps(payload).encode("utf-8")
        from urllib.request import Request, urlopen
        req = Request(url, data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"})
        with urlopen(req, timeout=10) as f:
            txt = f.read().decode("utf-8", errors="ignore")
            return True, txt[:2000]
    except Exception as e:
        return False, str(e)

def gather() -> Tuple[str, str]:
    lines: List[str] = []
    now = datetime.utcnow().isoformat()
    lines += [f"# Aurelia Progress Report", f"Generated: {now} UTC", ""]
    lines += [
        "## System",
        f"- Platform: {platform.platform()}",
        f"- Python: {platform.python_version()} ({sys.executable})",
        f"- CPU count: {os.cpu_count()}",
        f"- RAM: (install psutil for detailed RAM)",
        f"- GPU VRAM: {gpu_vram_info()}",
        ""
    ]
    path, models, url, code, raw = discover_ollama_models(BASE_OLLAMA)
    selected = choose_model(models)
    lines += [
        "## Ollama Discovery",
        f"- Base: {BASE_OLLAMA}",
        f"- Path matched: {path or 'none'} (http {code})",
        f"- Models: {', '.join(models) if models else '(none)'}",
        f"- Selected model: {selected}",
        ""
    ]
    ok_imp, msg_imp = import_health()
    ok_fa,  msg_fa  = fastapi_probe()
    ok_uv,  msg_uv  = bounded_uvicorn_probe()
    lines += [
        "## Backend Health",
        f"- import gateway.app: {'OK' if ok_imp else 'FAIL'} ({msg_imp})",
        f"- /healthz probe: {'OK' if ok_fa else 'FAIL'} ({msg_fa})",
        f"- uvicorn probe: {'OK' if ok_uv else 'FAIL'}",
        ""
    ]
    lines += ["## Chat Probe"]
    if selected != "none":
        ok_chat, msg_chat = chat_probe(selected, BASE_OLLAMA)
        lines += [f"- Using model: {selected} -> {'OK' if ok_chat else 'FAIL'}", f"```\n{msg_chat}\n```"]
    else:
        lines += ["- No model available to probe."]
    full = "\n".join(lines)
    return full, selected

def write_full_report(report_text: str):
    _ensure_dirs()
    OUT_MD.write_text(str(report_text), encoding="utf-8")

def append_digest_runtime(selected_model: str):
    _ensure_dirs()
    if not DIGEST_MD.exists():
        DIGEST_MD.write_text("# Elysia Digest\n\n", encoding="utf-8")
    entry = [
        "## Runtime Check",
        f"- Default provider: Ollama ({BASE_OLLAMA})",
        f"- Default model: {selected_model}",
        f"- Generated: {datetime.utcnow().isoformat()} UTC",
        ""
    ]
    with open(DIGEST_MD, "a", encoding="utf-8") as f:
        f.write("\n".join(entry))

# --- small stdlib helper for suppress ---
import contextlib

def main():
    try:
        report, selected = gather()
    except Exception as e:
        report, selected = f"# Aurelia Progress Report\nError during gather: {e}", "none"
    write_full_report(report)
    append_digest_runtime(selected)
    print(f"Wrote {OUT_MD}")
    print(f"Updated {DIGEST_MD}")


def run_reporter():
    """Compatibility wrapper for older callers that expect `run_reporter`.

    Starts the reporter once (same behavior as running the module directly).
    """
    return main()

if __name__ == "__main__":
    main()
