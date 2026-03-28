"""Parse Agent Box terminal output into structured chat messages."""

import re

# Terminal UI noise to skip entirely
_NOISE_PATTERNS = [
    re.compile(r"bypass\s+permissions", re.IGNORECASE),
    re.compile(r"shift\+tab\s+to\s+cycle", re.IGNORECASE),
    re.compile(r"^\s*[⏵⏴⏶⏷]+"),
    re.compile(r"^[\s\u2500-\u257f\u2580-\u259f\u25a0-\u25ff─━│┃═║\-=|]+$"),  # decorative lines
    re.compile(r"^\s*\d+[A-Z]?\s*$"),  # bare escape remnants like "240B"
    re.compile(r"Cogitated|Crunched|Churned", re.IGNORECASE),
    re.compile(r"ctrl\+o\s+to\s+expand", re.IGNORECASE),
    re.compile(r"^\s*[✻●]\s*(Cogitated|Crunched|Churned)", re.IGNORECASE),
]


def _is_noise(line: str) -> bool:
    return any(p.search(line) for p in _NOISE_PATTERNS)


def parse_terminal_output(output: str) -> list[dict]:
    messages: list[dict] = []
    lines = output.splitlines()
    i = 0
    current_role: str | None = None
    current_text: list[str] = []

    def flush():
        nonlocal current_role, current_text
        if current_role and current_text:
            text = "\n".join(current_text).strip()
            if text and not _is_noise(text):
                messages.append({"role": current_role, "type": "text", "content": text})
        current_role = None
        current_text = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty and noise lines
        if not stripped or _is_noise(stripped):
            i += 1
            continue

        # User prompt — collect all lines until next marker
        if stripped.startswith("\u276f") or (stripped.startswith(">") and not stripped.startswith(">>")):
            flush()
            prompt_lines = [stripped[1:].strip()]
            i += 1
            while i < len(lines):
                l = lines[i].strip()
                if l.startswith("\u25cf") or l.startswith("\u276f") or l.startswith("\u23bf") or (l.startswith(">") and not l.startswith(">>")):
                    break
                if l and not _is_noise(l):
                    prompt_lines.append(l)
                i += 1
            prompt = "\n".join(prompt_lines).strip()
            if prompt and not prompt.startswith("/"):
                messages.append({"role": "user", "type": "text", "content": prompt})
            continue

        # Assistant block (starts with ●)
        if stripped.startswith("\u25cf"):
            flush()
            text = stripped[1:].strip()

            # Skip noise after ●
            if not text or _is_noise(text):
                i += 1
                continue

            _TOOL_PREFIXES = ("Bash(", "Read(", "Edit(", "Write(", "Glob(", "Grep(", "Agent(", "Search(", "Fetch(")
            is_tool = ("(MCP)" in text) or any(text.startswith(p) or (" " + p) in text for p in _TOOL_PREFIXES)
            if is_tool:
                tool_name = text.split("(")[0].split(" - ")[-1].strip() if " - " in text else text.split("(")[0].strip()
                # For tool_use, collect continuation lines (e.g., multi-line MCP call)
                full_text = text
                i += 1
                while i < len(lines):
                    l = lines[i].strip()
                    if l.startswith("\u25cf") or l.startswith("\u276f") or l.startswith("\u23bf"):
                        break
                    if _is_noise(l):
                        i += 1
                        continue
                    # Stop if it looks like a new block
                    if l.startswith(">") and not l.startswith(">>"):
                        break
                    full_text += " " + l
                    i += 1
                messages.append({
                    "role": "assistant", "type": "tool_use",
                    "tool_name": tool_name, "content": full_text,
                })
            else:
                current_role = "assistant"
                current_text = [text]
                i += 1
            continue

        # Tool result (starts with ⎿)
        if stripped.startswith("\u23bf"):
            flush()
            result_text = stripped[1:].strip()
            i += 1
            while i < len(lines):
                l = lines[i].strip()
                if l.startswith("\u25cf") or l.startswith("\u276f") or (l.startswith(">") and not l.startswith(">>")):
                    break
                if l.startswith("\u23bf"):
                    result_text += "\n" + l[1:].strip()
                elif l and not _is_noise(l):
                    result_text += "\n" + l
                i += 1
            messages.append({
                "role": "assistant", "type": "tool_result",
                "content": result_text[:5000],
                "is_error": False,
            })
            continue

        # Continuation of current block
        if current_role and stripped and not _is_noise(stripped):
            current_text.append(stripped)

        i += 1

    flush()
    return messages
