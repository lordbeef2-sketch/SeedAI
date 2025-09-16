import psutil
import requests
import time
import threading
from pathlib import Path

try:
    import pynvml
    nvidia_available = True
    pynvml.nvmlInit()
except ImportError:
    nvidia_available = False

BASE_DIR = Path(__file__).resolve().parents[1]
DIGEST_PATH = BASE_DIR / "ElysiaDigest" / "latest" / "digest.md"
REPORT_PATH = BASE_DIR / "diagnostics" / "progress_report.md"
GATEWAY_URL = "http://127.0.0.1:8088"

def get_system_info():
    info = {}

    # Default model
    try:
        with open(BASE_DIR / "config" / "llm_config.json", "r") as f:
            import json
            cfg = json.load(f)
            info["default_model"] = cfg.get("model", "unknown")
    except Exception:
        info["default_model"] = "unknown"

    # VRAM
    if nvidia_available:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info["vram_used"] = mem_info.used // (1024**3)  # GB
            info["vram_total"] = mem_info.total // (1024**3)  # GB
        except Exception:
            info["vram_used"] = "N/A"
            info["vram_total"] = "N/A"
    else:
        info["vram_used"] = "N/A"
        info["vram_total"] = "N/A"

    # RAM
    ram = psutil.virtual_memory()
    info["ram_used"] = ram.used // (1024**3)  # GB
    info["ram_total"] = ram.total // (1024**3)  # GB

    # CPU
    info["cpu_load"] = psutil.cpu_percent(interval=1)

    # Probes
    try:
        resp = requests.get(f"{GATEWAY_URL}/api/models", timeout=5)
        info["models_probe"] = "PASS" if resp.status_code == 200 else "FAIL"
    except Exception:
        info["models_probe"] = "FAIL"

    try:
        resp = requests.get(f"{GATEWAY_URL}/healthz", timeout=5)
        info["health_probe"] = "PASS" if resp.status_code == 200 else "FAIL"
    except Exception:
        info["health_probe"] = "FAIL"

    return info

def write_summary(info):
    summary = f"- Default model: {info['default_model']}\n"
    if info['vram_used'] != "N/A":
        summary += f"- VRAM usage: {info['vram_used']} GB / {info['vram_total']} GB\n"
    else:
        summary += "- VRAM usage: N/A\n"
    summary += f"- RAM usage: {info['ram_used']} GB / {info['ram_total']} GB\n"
    summary += f"- CPU usage: {info['cpu_load']}%\n"
    summary += f"- Models probe: {info['models_probe']}\n"
    summary += f"- Health probe: {info['health_probe']}\n"

    try:
        with open(DIGEST_PATH, "a") as f:
            f.write("\n## Runtime Check\n")
            f.write(summary)
    except Exception as e:
        print(f"Failed to write digest: {e}")

def write_full_report(info):
    report = f"Progress Report - {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += f"Default Model: {info['default_model']}\n\n"
    report += f"System Resources:\n"
    report += f"- VRAM: {info['vram_used']} / {info['vram_total']} GB\n"
    report += f"- RAM: {info['ram_used']} / {info['ram_total']} GB\n"
    report += f"- CPU Load: {info['cpu_load']}%\n\n"
    report += f"Health Probes:\n"
    report += f"- Models API: {info['models_probe']}\n"
    report += f"- Health Endpoint: {info['health_probe']}\n"

    try:
        with open(REPORT_PATH, "w") as f:
            f.write(report)
    except Exception as e:
        print(f"Failed to write report: {e}")

def run_reporter():
    while True:
        info = get_system_info()
        write_summary(info)
        write_full_report(info)
        time.sleep(60)  # Every minute

if __name__ == "__main__":
    run_reporter()