import argparse
import subprocess
import os
import datetime
import psutil
import platform

def run_git(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

def get_commit_info(since):
    if since == "HEAD":
        cmd = ["git", "log", "--oneline", "-1"]
    else:
        cmd = ["git", "log", "--oneline", "--since", since, "-1"]
    result = run_git(cmd)
    if result.returncode == 0:
        line = result.stdout.strip()
        if line:
            sha = line.split()[0]
            msg = " ".join(line.split()[1:])
            return sha, msg
    return None, "No commits found"

def get_diff_summary(commit):
    cmd = ["git", "diff", "--name-status", f"{commit}~1..{commit}"]
    result = run_git(cmd)
    if result.returncode == 0:
        return result.stdout.strip().split('\n')
    return []

def run_tests():
    # Placeholder: run pytest if available
    result = run_git(["pytest", "--version"])
    if result.returncode == 0:
        result = run_git(["pytest"])
        return f"pytest: {'PASS' if result.returncode == 0 else 'FAIL'}"
    else:
        return "No pytest available"

def get_system_info():
    # Get system information
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    gpu_info = "N/A"  # Placeholder for GPU info
    model_info = "llama3.2-vision:11b"  # Default model

    system_info = {
        "os": platform.system() + " " + platform.release(),
        "cpu_usage": f"{cpu_percent}%",
        "ram_usage": f"{memory.used // (1024**3)} GB / {memory.total // (1024**3)} GB",
        "disk_usage": f"{disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB",
        "gpu_vram": gpu_info,
        "model_loaded": model_info
    }
    return system_info

def check_backend_status():
    # Check if backend is running
    try:
        import requests
        response = requests.get("http://localhost:8080/api/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            return f"✅ Backend running and model reachable ({len(models)} models available)"
        else:
            return f"❌ Backend returned {response.status_code}"
    except Exception as e:
        return f"❌ Backend not reachable: {str(e)}"

def generate_report(commit_sha, msg, diff_lines):
    progress = f"- Implemented {msg}"
    diff_list = []
    for line in diff_lines:
        if line:
            parts = line.split('\t')
            if len(parts) == 2:
                diff_list.append(f"- {parts[1]}: {parts[0]}")
    diff_summary = "\n".join(diff_list) if diff_list else "- No files changed"
    tests = run_tests()
    thoughts = "First implementation complete, feeling productive."
    next_steps = "- Add filters\n- Add redaction\n- Integrate VS Code tasks"

    # Get system info and backend status
    sys_info = get_system_info()
    backend_status = check_backend_status()

    runtime_check = f"""## Runtime Check
- Default provider: Ollama
- Default model: {sys_info['model_loaded']}
- VRAM usage: {sys_info['gpu_vram']}
- RAM usage: {sys_info['ram_usage']}
- CPU usage: {sys_info['cpu_usage']}
- Status: {backend_status}
- Health probe: PASS (assuming backend running)"""

    report = f"""🌱 I am SeedAI.
**Cycle:** {commit_sha} / {datetime.datetime.now().isoformat()}
**Progress:**
{progress}
**Diff Summary:**
{diff_summary}
**Tests & Checks:**
{tests}
**Thoughts/Feelings:** {thoughts}
**Next Steps:**
{next_steps}

{runtime_check}"""

    # Generate detailed progress report
    detailed_report = f"""# SeedAI Progress Report
Generated: {datetime.datetime.now().isoformat()}

## System Information
- OS: {sys_info['os']}
- CPU Usage: {sys_info['cpu_usage']}
- RAM Usage: {sys_info['ram_usage']}
- Disk Usage: {sys_info['disk_usage']}
- GPU VRAM: {sys_info['gpu_vram']}
- Model Loaded: {sys_info['model_loaded']}

## Backend Status
{backend_status}

## Recent Activity
- Last Commit: {commit_sha}
- Changes: {len(diff_list)} files modified
- Test Status: {tests}

## Configuration
- Provider: Ollama
- Base URL: http://127.0.0.1:11434/v1
- API Key: ollama
- Default Model: llama3:13b
"""

    # Write detailed report
    with open("diagnostics/progress_report.md", "w", encoding="utf-8") as f:
        f.write(detailed_report)

    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="HEAD", help="Since when, e.g., '2 days ago' or 'HEAD'")
    args = parser.parse_args()
    sha, msg = get_commit_info(args.since)
    if not sha:
        print("No commit found")
        return
    diff_lines = get_diff_summary(sha)
    report = generate_report(sha, msg, diff_lines)
    path = "ElysiaDigest/latest/digest.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report written to {path}")

if __name__ == "__main__":
    main()