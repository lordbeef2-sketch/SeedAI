"""import psutil

Progress reporter for Aurelia (SeedAI).import requests

Writes diagnostics/progress_report.md (full) and appends a Runtime Check to ElysiaDigest/latest/digest.md.import time

Safe, idempotent, and relies on stdlib where possible.import threading

"""from pathlib import Path



from __future__ import annotationstry:

import os, sys, subprocess, json, platform, shutil, time, socket    import pynvml

from pathlib import Path    nvidia_available = True

from datetime import datetime    pynvml.nvmlInit()

except ImportError:

ROOT = Path(__file__).resolve().parents[1]    nvidia_available = False

DIAG_DIR = ROOT / "diagnostics"

DIAG_DIR.mkdir(parents=True, exist_ok=True)BASE_DIR = Path(__file__).resolve().parents[1]

OUT_MD = DIAG_DIR / "progress_report.md"DIGEST_PATH = BASE_DIR / "ElysiaDigest" / "latest" / "digest.md"

DIGEST_DIR = ROOT / "ElysiaDigest" / "latest"REPORT_PATH = BASE_DIR / "diagnostics" / "progress_report.md"

DIGEST_DIR.mkdir(parents=True, exist_ok=True)GATEWAY_URL = "http://127.0.0.1:8088"

DIGEST_MD = DIGEST_DIR / "digest.md"

def get_system_info():

BASE_OLLAMA = "http://127.0.0.1:11434"    info = {}

OLLAMA_API_PATHS = ("/v1/models","/models","/api/tags","/v1/tags","/v1/engines")

    # Default model

def try_cmd(cmd, timeout=10, cwd=None):    try:

    try:        with open(BASE_DIR / "config" / "llm_config.json", "r") as f:

        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd, timeout=timeout, shell=False)            import json

        return p.returncode, p.stdout.strip()            cfg = json.load(f)

    except subprocess.TimeoutExpired as e:            info["default_model"] = cfg.get("model", "unknown")

        return 124, f"Timeout after {timeout}s"    except Exception:

    except FileNotFoundError as e:        info["default_model"] = "unknown"

        return 127, f"Not found: {e}"

    # VRAM

def http_get(url, timeout=5):    if nvidia_available:

    """Try simple GET using requests if available, else urllib."""        try:

    try:            handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        import requests            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

        r = requests.get(url, timeout=timeout)            info["vram_used"] = mem_info.used // (1024**3)  # GB

        return r.status_code, r.text            info["vram_total"] = mem_info.total // (1024**3)  # GB

    except Exception:        except Exception:

        try:            info["vram_used"] = "N/A"

            from urllib.request import urlopen, Request            info["vram_total"] = "N/A"

            req = Request(url, headers={"User-Agent":"Aurelia-Reporter/1.0"})    else:

            with urlopen(req, timeout=timeout) as f:        info["vram_used"] = "N/A"

                return f.getcode(), f.read().decode("utf-8", errors="ignore")        info["vram_total"] = "N/A"

        except Exception as e:

            return None, str(e)    # RAM

    ram = psutil.virtual_memory()

def find_ollama_models(base=BASE_OLLAMA):    info["ram_used"] = ram.used // (1024**3)  # GB

    found = []    info["ram_total"] = ram.total // (1024**3)  # GB

    for p in OLLAMA_API_PATHS:

        url = base.rstrip("/") + p    # CPU

        code, txt = http_get(url)    info["cpu_load"] = psutil.cpu_percent(interval=1)

        if code and code < 400:

            # best-effort parse    # Probes

            try:    try:

                data = json.loads(txt)        resp = requests.get(f"{GATEWAY_URL}/api/models", timeout=5)

                # try common shapes        info["models_probe"] = "PASS" if resp.status_code == 200 else "FAIL"

                if isinstance(data, dict) and "models" in data:    except Exception:

                    found = [m.get("name") or m for m in data["models"]]        info["models_probe"] = "FAIL"

                elif isinstance(data, list):

                    # list of strings or dicts    try:

                    found = [ (item.get("name") if isinstance(item, dict) else str(item)) for item in data ]        resp = requests.get(f"{GATEWAY_URL}/healthz", timeout=5)

                else:        info["health_probe"] = "PASS" if resp.status_code == 200 else "FAIL"

                    # fallback: search for tokens like 'llama' or 'gemma'    except Exception:

                    found = list({w for w in txt.split() if "llama" in w or "gemma" in w})        info["health_probe"] = "FAIL"

            except Exception:

                found = list({w for w in txt.split() if "llama" in w or "gemma" in w})    return info

        if found:

            return p, found, url, code, txtdef write_summary(info):

    return None, [], None, None, "no endpoint reachable"    summary = f"- Default model: {info['default_model']}\n"

    if info['vram_used'] != "N/A":

def gpu_vram_info():        summary += f"- VRAM usage: {info['vram_used']} GB / {info['vram_total']} GB\n"

    # best-effort: try torch, then nvidia-smi, else unknown    else:

    try:        summary += "- VRAM usage: N/A\n"

        import torch    summary += f"- RAM usage: {info['ram_used']} GB / {info['ram_total']} GB\n"

        if torch.cuda.is_available():    summary += f"- CPU usage: {info['cpu_load']}%\n"

            idx = 0    summary += f"- Models probe: {info['models_probe']}\n"

            mem = torch.cuda.get_device_properties(idx).total_memory    summary += f"- Health probe: {info['health_probe']}\n"

            used = torch.cuda.memory_allocated(idx)

            return f"cuda:{idx} total={mem//1024**2}MB used={used//1024**2}MB"    try:

    except Exception:        with open(DIGEST_PATH, "a") as f:

        pass            f.write("\n## Runtime Check\n")

    # try nvidia-smi            f.write(summary)

    rc, out = try_cmd(["nvidia-smi","--query-gpu=memory.total,memory.used","--format=csv,noheader,nounits"], timeout=3)    except Exception as e:

    if rc == 0 and out:        print(f"Failed to write digest: {e}")

        return out.strip()

    return "unknown (no torch/nvidia-smi or AMD GPU)"def write_full_report(info):

    report = f"Progress Report - {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

def safe_import(module_name):    report += f"Default Model: {info['default_model']}\n\n"

    try:    report += f"System Resources:\n"

        __import__(module_name)    report += f"- VRAM: {info['vram_used']} / {info['vram_total']} GB\n"

        return True, None    report += f"- RAM: {info['ram_used']} / {info['ram_total']} GB\n"

    except Exception as e:    report += f"- CPU Load: {info['cpu_load']}%\n\n"

        return False, str(e)    report += f"Health Probes:\n"

    report += f"- Models API: {info['models_probe']}\n"

def test_fastapi_health():    report += f"- Health Endpoint: {info['health_probe']}\n"

    try:

        from importlib import import_module    try:

        mm = import_module("gateway.app")        with open(REPORT_PATH, "w") as f:

        app = getattr(mm, "app", None)            f.write(report)

        if app is None:    except Exception as e:

            return False, "module loaded but 'app' not found"        print(f"Failed to write report: {e}")

        # try TestClient

        try:def run_reporter():

            from fastapi.testclient import TestClient    while True:

            with TestClient(app) as client:        info = get_system_info()

                r = client.get("/healthz")        write_summary(info)

                return (r.status_code == 200), f"{r.status_code} {r.text}"        write_full_report(info)

        except Exception as e:        time.sleep(60)  # Every minute

            return False, f"TestClient fail: {e}"

    except Exception as e:if __name__ == "__main__":

        return False, f"Import fail: {e}"    run_reporter()

def bounded_uvicorn_probe(app_path="gateway.app:app", port=8000, wait_s=5):
    # run uvicorn as python -m uvicorn ... (no reload), capture output for wait_s seconds
    cmd = [sys.executable, "-m", "uvicorn", app_path, "--host", "127.0.0.1", "--port", str(port), "--log-level", "info"]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        return False, f"Failed to start uvicorn: {e}"
    try:
        time.sleep(wait_s)
        out = ""
        try:
            out = p.stdout.read()
        except Exception:
            pass
        # then kill
        p.kill()
        return True, out.strip()[:8192]
    except Exception as e:
        try:
            p.kill()
        except Exception:
            pass
        return False, f"Probe error: {e}"

def probe_chat_send(model_name, base=BASE_OLLAMA):
    # best-effort chat test using OpenAI-compatible endpoint shape
    url = base.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role":"user","content":"Hello Aurelia"}],
        "max_tokens": 32
    }
    try:
        import requests
        r = requests.post(url, json=payload, timeout=8)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)

def write_full_report(report_text):
    OUT_MD.write_text(report_text, encoding="utf-8")

def append_digest_runtime(entry_lines):
    header = "## Runtime Check"
    body = "\n".join(["- " + l for l in entry_lines])
    block = f"\n{header}\n{body}\n"
    # ensure digest exists
    if not DIGEST_MD.exists():
        DIGEST_MD.write_text("# Elysia Digest\n\n", encoding="utf-8")
    with open(DIGEST_MD, "a", encoding="utf-8") as f:
        f.write(block)

def gather():
    lines = []
    now = datetime.utcnow().isoformat()
    lines.append(f"# Aurelia Progress Report")
    lines.append(f"Generated: {now} UTC")
    lines.append("")
    lines.append("## System")
    lines.append(f"- Platform: {platform.platform()}")
    lines.append(f"- Python: {platform.python_version()} ({sys.executable})")
    lines.append(f"- CPU count: {os.cpu_count()}")
    try:
        import psutil
        mem = psutil.virtual_memory()
        lines.append(f"- RAM: {mem.used//1024**2}MB used / {mem.total//1024**2}MB total")
    except Exception:
        lines.append("- RAM: psutil not installed (install for richer info)")
    # GPU
    lines.append(f"- GPU VRAM: {gpu_vram_info()}")
    lines.append("")
    # Ollama probe
    p, models, url, code, raw = find_ollama_models()
    lines.append("## Ollama / Model discovery")
    if models:
        lines.append(f"- Endpoint path matched: {p} @ {url} (http {code})")
        lines.append(f"- Models found: {', '.join(models)}")
    else:
        lines.append(f"- No Ollama models discovered. probe result: {raw}")
    lines.append("")
    # import tests
    lines.append("## Import & Health checks")
    ok_app, msg_app = safe_import("gateway.app")
    lines.append(f"- import gateway.app: {'OK' if ok_app else 'FAIL'} {msg_app or ''}")
    ok_health, msg_health = test_fastapi_health()
    lines.append(f"- FastAPI health probe: {'OK' if ok_health else 'FAIL'} {msg_health}")
    # bounded uvicorn
    lines.append("## Uvicorn probe")
    started, uvout = bounded_uvicorn_probe()
    lines.append(f"- uvicorn start probe: {'OK' if started else 'FAIL'}")
    if uvout:
        lines.append(f"- uvicorn output (truncated):\n```\n{uvout}\n```")
    # quick chat probe if model available
    lines.append("")
    lines.append("## Chat probe")
    if models:
        model_to_test = models[0]
        ok_chat, chat_resp = probe_chat_send(model_to_test)
        lines.append(f"- probe model: {model_to_test} -> {'OK' if ok_chat else 'FAIL'}")
        if chat_resp:
            lines.append(f"- response (truncated):\n```\n{chat_resp[:2000]}\n```")
    else:
        lines.append("- No model to probe.")
    # pytest quick run
    lines.append("")
    lines.append("## Tests (quick)")
    rc, out = try_cmd([sys.executable, "-m", "pytest", "-q", "-k", "health"], timeout=60)
    lines.append(f"- pytest health: rc={rc}")
    lines.append(f"```\n{(out or '')[:4000]}\n```")
    # finalize
    full = "\n".join(lines)
    return full, models

def main():
    report, models = gather()
    write_full_report(report)
    # append digest summary
    default_model = (models[0] if models else "none")
    entry = [
        f"Default provider: Ollama ({BASE_OLLAMA})",
        f"Default model: {default_model}",
        f"Status: {'✅ Backend running and model reachable' if models else '❌ model not reachable'}",
        f"Generated: {datetime.utcnow().isoformat()} UTC"
    ]
    append_digest_runtime(entry)
    print("Progress report written to", OUT_MD)
    print("Digest appended at", DIGEST_MD)

if __name__ == "__main__":
    main()