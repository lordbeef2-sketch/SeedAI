"""Memory bootstrapper for Aurelia.

Provides `load_bootstrap_messages()` which returns a list of OpenAI-style
system messages to prepend to chat requests.

Behavior:
- Reads `seedai/persona_aurelia.md` and includes as a system message (if present).
- Reads `seedai/memory/core.json` and includes a compact JSON summary as a system message.
- Reads the last ~2000 characters of `ElysiaDigest/latest/digest.md` (if present)
  and includes it as a 'Recent digest entries' system message.
- Truncates combined bootstrap content to `AURELIA_BOOTSTRAP_MAX` characters
  (default 4000), preferring to truncate the digest.
- Robust: missing or malformed files are skipped silently.
"""

import json
import os
from pathlib import Path
from typing import List, Dict

DEFAULT_MAX = int(os.environ.get("AURELIA_BOOTSTRAP_MAX", "4000"))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _compact_json_summary(data: dict) -> str:
    """Produce a compact textual summary from core.json suitable for a system message."""
    try:
        identity = data.get("identity", {})
        relationships = data.get("relationships", {})
        capabilities = data.get("capabilities", [])
        principles = data.get("principles", [])

        parts = []
        if identity:
            parts.append(f"Identity: {identity.get('name', '')} — {identity.get('role', '')}. {identity.get('description', '')}")
        if relationships:
            rel_items = ", ".join([f"{k}: {v}" for k, v in relationships.items()])
            parts.append(f"Relationships: {rel_items}")
        if capabilities:
            parts.append("Capabilities: " + "; ".join(capabilities))
        if principles:
            parts.append("Principles: " + "; ".join(principles))

        return "\n".join(parts)
    except Exception:
        return json.dumps(data)


def load_bootstrap_messages() -> List[Dict[str, str]]:
    """Load bootstrap system messages for Aurelia.

    Returns a list of dicts like {"role":"system","content":"..."}.
    This function is idempotent and will silently skip missing/invalid files.
    Total returned content length will be trimmed to DEFAULT_MAX (env override).
    """
    msgs: List[Dict[str, str]] = []

    root = Path(__file__).resolve().parents[1]

    # 1) persona file
    try:
        persona_path = Path(os.environ.get("AURELIA_PERSONA_PATH", root / "seedai/persona_aurelia.md"))
        persona_text = _read_text(persona_path)
        if persona_text:
            msgs.append({"role": "system", "content": persona_text.strip()})
    except Exception:
        pass

    # 2) core.json
    try:
        core_path = root / "seedai" / "memory" / "core.json"
        if core_path.exists():
            raw = core_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            summary = _compact_json_summary(data)
            if summary:
                msgs.append({"role": "system", "content": "Core memory summary:\n" + summary})
    except Exception:
        pass

    # 3) recent digest
    try:
        digest_path = root / "ElysiaDigest" / "latest" / "digest.md"
        digest_text = _read_text(digest_path)
        if digest_text:
            # include up to ~2000 chars from the end, but overall cap enforced later
            tail = digest_text[-2000:]
            msgs.append({"role": "system", "content": "Recent digest entries:\n" + tail})
    except Exception:
        pass

    # Truncate combined messages if necessary, preferring to trim the digest message
    max_chars = int(os.environ.get("AURELIA_BOOTSTRAP_MAX", DEFAULT_MAX))
    combined = "\n\n".join(m["content"] for m in msgs)
    if len(combined) <= max_chars:
        return msgs

    # Need to trim. Find digest message (last one if present) and truncate it first.
    for i in range(len(msgs)-1, -1, -1):
        if msgs[i]["content"].startswith("Recent digest entries:"):
            prefix = "Recent digest entries:\n"
            content = msgs[i]["content"][len(prefix):]
            # available space after removing other messages
            others = "\n\n".join(m["content"] for j, m in enumerate(msgs) if j != i)
            remaining = max_chars - len(others) - len(prefix) - 6
            if remaining <= 0:
                # remove digest entirely
                del msgs[i]
            else:
                msgs[i]["content"] = prefix + (content[-remaining:])
            break

    # If still too long, iteratively truncate other messages from the end
    while True:
        combined = "\n\n".join(m["content"] for m in msgs)
        if len(combined) <= max_chars:
            break
        # truncate the longest message (except persona) or drop last
        lengths = [(len(m["content"]), idx) for idx, m in enumerate(msgs)]
        lengths.sort(reverse=True)
        _, idx = lengths[0]
        if len(msgs[idx]["content"]) > 100:
            msgs[idx]["content"] = msgs[idx]["content"][-1000:]
        else:
            del msgs[idx]
        if not msgs:
            break

    return msgs
