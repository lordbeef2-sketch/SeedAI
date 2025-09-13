#!/usr/bin/env python3
"""
SeedAI/OpenWebUI Validator & Collector
- Runs health checks on the gateway (models, chat)
- Verifies CORS/auth basics
- Collects key source files and small log samples
- Writes a JSON report + bundles artifacts into a ZIP (≤ 500 MB)

Usage:
  python scripts/seedai_validate.py --base-url http://127.0.0.1:8088/v1 --api-key changeme

Optional:
  --owui http://localhost:5173           # used only for report (no requests)
  --chat "hello"                          # test prompt
  --out seedai_validation.zip             # output zip
"""

import argparse, io, json, os, re, socket, subprocess, sys, time, zipfile
from pathlib import Path
from typing import List, Dict, Any, Tuple
import requests

# ---------- Config (edit if needed) ----------
DEFAULT_GW = "http://127.0.0.1:8088/v1"
DEFAULT_KEY = "changeme"
CHAT_PROMPT = "hello from validator"
# File collection: (glob, max_bytes_per_file)
COLLECT_GLOBS = [
    ("gateway/app.py", 256_000),
    ("gateway/routes/*.py", 256_000),
    ("gateway/security/*.py", 128_000),
    ("gateway/*.py", 128_000),
    ("SeedAI/seedai_reasoner.py", 512_000),
    ("seedai_reasoner.py", 512_000),
    ("scripts/seedai_child_cli.py", 128_000),
    ("SeedAI/config/llm_config.json", 64_000),
    (".env", 32_000),                     # if present; redact below
    ("gateway/.env", 32_000),
    ("launcher/.env", 32_000),
    ("open-webui/backend/.env", 32_000),
]
# Log collection (best effort; each truncated)
LOG_GLOBS = [
    ("data/gateway.log", 1_000_000),
    ("open-webui/backend/*.log", 1_000_000),
]
# Total ZIP size cap (hard stop)
ZIP_CAP_BYTES = 500 * 1024 * 1024
# --------------------------------------------

REDACT_KEYS = {"API_KEY", "OPENAI_API_KEY", "GATEWAY_API_KEY", "AUTH", "PASSWORD", "SECRET", "TOKEN"}

def truncate(b: bytes, n: int) -> bytes:
    return b if len(b) <= n else b[:n] + b"\n\n[...truncated...]\n".encode()

def redact_env(text: str) -> str:
    out = []
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            if any(key in k.upper() for key in REDACT_KEYS):
                v = "***redacted***"
            out.append(f"{k}={v}")
        else:
            out.append(line)
    return "\n".join(out)

def port_is_open(host: str, port: int, timeout=0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def curl_json(url: str, key: str = None, method: str = "GET", json_body: Any = None, timeout=15) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    headers["Content-Type"] = "application/json"
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=timeout)
        else:
            r = requests.post(url, headers=headers, json=json_body, timeout=timeout)
        try:
            data = r.json()
        except Exception:
            data = {"_raw": r.text[:4000]}
        return r.status_code, dict(r.headers), data
    except requests.RequestException as e:
        return 0, {}, {"error": str(e)}

def collect_files(base: Path, patterns: List[Tuple[str,int]], ziph: zipfile.ZipFile, report: Dict[str,Any]) -> int:
    added = 0
    for glob, max_bytes in patterns:
        for p in base.glob(glob):
            try:
                b = p.read_bytes()
                if p.name == ".env" or p.suffix == ".env":
                    try:
                        b = redact_env(b.decode("utf-8", "ignore")).encode()
                    except Exception:
                        pass
                b = truncate(b, max_bytes)
                ziph.writestr(str(p), b)
                added += len(b)
                report.setdefault("collected_files", []).append({"path": str(p), "bytes": len(b)})
            except Exception as e:
                report.setdefault("collect_errors", []).append({"path": str(p), "error": str(e)})
    return added

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_GW)
    parser.add_argument("--api-key", default=DEFAULT_KEY)
    parser.add_argument("--chat", default=CHAT_PROMPT)
    parser.add_argument("--owui", default="http://localhost:5173")
    parser.add_argument("--out", default="seedai_validation.zip")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    api_key = args.api_key
    out_zip = Path(args.out).resolve()
    repo = Path.cwd()

    report: Dict[str, Any] = {
        "ts": int(time.time()),
        "base_url": base_url,
        "owui_url": args.owui,
        "env": {
            "CORS_ORIGINS": os.getenv("CORS_ORIGINS"),
            "ALLOWED_IPS": os.getenv("ALLOWED_IPS"),
            "PORT": os.getenv("PORT"),
        },
        "ports": {},
        "checks": {}
    }

    # Ports quick check (best-effort guesses)
    report["ports"]["gateway_8088"] = port_is_open("127.0.0.1", 8088)
    report["ports"]["owui_5173"] = port_is_open("127.0.0.1", 5173)
    report["ports"]["ollama_11434"] = port_is_open("127.0.0.1", 11434)

    # Health
    status, headers, data = curl_json(base_url.replace("/v1","") + "/healthz")
    report["checks"]["healthz"] = {"status": status, "headers": headers, "data": data}

    # Models
    status, headers, data = curl_json(f"{base_url}/models", key=api_key)
    report["checks"]["models"] = {"status": status, "headers": headers, "data": data}
    model_ok = (status == 200) and isinstance(data, dict) and "data" in data and any(d.get("id") == "seedai" for d in data.get("data", []))

    # Chat
    body = {
        "model": "seedai",
        "messages": [{"role": "user", "content": args.chat}],
    }
    status, headers, data = curl_json(f"{base_url}/chat/completions", key=api_key, method="POST", json_body=body)
    report["checks"]["chat"] = {"status": status, "headers": headers, "data": data}
    chat_ok = (status == 200) and isinstance(data, dict) and data.get("object") == "chat.completion"

    # CORS sanity (string-level hints)
    cors = os.getenv("CORS_ORIGINS", "")
    report["hints"] = []
    if cors and "." in cors and "," not in cors and "http" in cors and "localhost" in cors:
        report["hints"].append("CORS_ORIGINS looks like a single URL but may be split incorrectly; ensure code uses .split(',') not .split('.')")

    # Git summary
    try:
        rev = subprocess.check_output(["git","rev-parse","--short","HEAD"], text=True).strip()
    except Exception:
        rev = None
    report["git"] = {"rev": rev}

    # Create ZIP with report + files (respect cap)
    total_bytes = 0
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # JSON report
        z.writestr("validator_report.json", json.dumps(report, indent=2))
        total_bytes += len(json.dumps(report))

        # Source files
        total_bytes += collect_files(repo, COLLECT_GLOBS, z, report)
        # Logs
        total_bytes += collect_files(repo, LOG_GLOBS, z, report)

        if total_bytes > ZIP_CAP_BYTES:
            raise SystemExit(f"ZIP would exceed {ZIP_CAP_BYTES} bytes; collected ~{total_bytes} bytes")

    # Print a human summary
    print("\n=== SeedAI/OpenWebUI Validation Summary ===")
    print(f"Base URL:       {base_url}")
    print(f"Health:         {report['checks']['healthz']['status']}")
    print(f"Models:         {report['checks']['models']['status']}  (seedai listed: {model_ok})")
    print(f"Chat:           {report['checks']['chat']['status']}    (OK: {chat_ok})")
    if report.get("hints"):
        print("Hints:")
        for h in report["hints"]:
            print(f" - {h}")
    print(f"ZIP written:    {out_zip}")
    print("==========================================\n")

if __name__ == "__main__":
    main()
