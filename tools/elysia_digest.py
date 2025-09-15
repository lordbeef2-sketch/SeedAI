import argparse
import subprocess
import os
import datetime

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
{next_steps}"""
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