"""Parse terminal output from Claude Code / Codex / Qwen into structured chat messages."""

import re

# Strip ANSI escape sequences (colors, cursor moves, etc.)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\].*?\x07|\x1b\[[\d;]*m")

# Assistant block markers:  ● (Claude U+25CF)  • (Codex U+2022)  ✦ (Qwen U+2726)
_ASSISTANT_MARKERS = ("\u25cf", "\u2022", "\u2726")

# Tool result markers:  ⎿ (Claude U+23BF)  └ (Codex U+2514)
_RESULT_MARKERS = ("\u23bf", "\u2514")

# Terminal UI noise to skip entirely
_NOISE_PATTERNS = [
    re.compile(r"bypass\s+permissions", re.IGNORECASE),
    re.compile(r"shift\+tab\s+to\s+cycle", re.IGNORECASE),
    re.compile(r"^\s*[⏵⏴⏶⏷]+"),
    re.compile(r"^[\s\u2500-\u257f\u2580-\u259f\u25a0-\u25ff\u2550-\u256c─━│┃═║\-=|]+$"),
    re.compile(r"^\s*\d+[A-Z]?\s*$"),
    re.compile(r"Cogitated|Crunched|Churned", re.IGNORECASE),
    re.compile(r"ctrl\+o\s+to\s+expand", re.IGNORECASE),
    re.compile(r"^\s*[✻●•]\s*(Cogitated|Crunched|Churned)", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*token", re.IGNORECASE),
    re.compile(r"^\s*(yes|no|auto)\s*$", re.IGNORECASE),
    re.compile(r"^\s*\(Y/n\)", re.IGNORECASE),
    re.compile(r"^[╭╰│]\s*[─]?", re.IGNORECASE),
    re.compile(r"^[·✻✢]\s+\S"),  # thinking/status (· Generating…, ✻ Baked, ✢ Vibing)
    re.compile(r"^\s*Generating|^\s*Thinking|^\s*Processing", re.IGNORECASE),
    re.compile(r"gpt-\S+\s+default\s+·", re.IGNORECASE),  # Codex status line
    re.compile(r"^\*\s+Type your message", re.IGNORECASE),  # Qwen input placeholder
    re.compile(r"YOLO mode\s+\(", re.IGNORECASE),  # Qwen YOLO status
    re.compile(r"^\s*\d+\.?\d*%\s+context\s+used", re.IGNORECASE),  # context usage
    re.compile(r"Tips:\s+Use /bug", re.IGNORECASE),  # Qwen tips
    re.compile(r"Qwen Code\s+\(v", re.IGNORECASE),  # Qwen header
    re.compile(r"API Key\s+\|", re.IGNORECASE),  # Qwen config line
    re.compile(r"^/workspace\s*$"),  # bare workspace path
]

_TOOL_PREFIXES = (
    "Bash(", "Read(", "Edit(", "Write(", "Glob(", "Grep(",
    "Agent(", "Search(", "Fetch(", "TodoWrite(", "WebSearch(",
    "WebFetch(", "NotebookEdit(", "Skill(",
)


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _is_noise(line: str) -> bool:
    return any(p.search(line) for p in _NOISE_PATTERNS)


# User prompt markers: ❯ (Claude U+276F)  > (ASCII)  › (Codex U+203A)
_USER_PROMPT_MARKERS = ("\u276f", "\u203a", ">")


def _is_user_prompt(stripped: str) -> bool:
    for m in _USER_PROMPT_MARKERS:
        if stripped.startswith(m) and not stripped.startswith(">>"):
            return True
    return False


def _starts_with_assistant(stripped: str) -> str | None:
    """Return the marker char if line starts with an assistant marker, else None."""
    for m in _ASSISTANT_MARKERS:
        if stripped.startswith(m):
            return m
    return None


def _starts_with_result(stripped: str) -> str | None:
    """Return the marker char if line starts with a result marker, else None."""
    for m in _RESULT_MARKERS:
        if stripped.startswith(m):
            return m
    return None


def _is_tool(text: str) -> bool:
    if "(MCP)" in text:
        return True
    # Codex style: "Called" followed by tool invocation on next line
    if text.lower().startswith("called"):
        return True
    return any(text.startswith(p) or (" " + p) in text for p in _TOOL_PREFIXES)


def _extract_tool_name(text: str) -> str:
    # Codex: "Called" → next content has the tool name
    if text.lower().startswith("called"):
        return "Called"
    if " - " in text:
        return text.split("(")[0].split(" - ")[-1].strip()
    return text.split("(")[0].strip()


def _is_any_marker(stripped: str) -> bool:
    """Check if line starts with any known marker."""
    return bool(_starts_with_assistant(stripped) or _starts_with_result(stripped) or _is_user_prompt(stripped))


def parse_terminal_output(output: str) -> list[dict]:
    output = _strip_ansi(output)
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

        if not stripped or _is_noise(stripped):
            i += 1
            continue

        # ── User prompt ──
        if _is_user_prompt(stripped):
            flush()
            # Determine which marker was used
            prompt_char = ">"
            for m in _USER_PROMPT_MARKERS:
                if stripped.startswith(m):
                    prompt_char = m
                    break
            prompt_lines = [stripped[len(prompt_char):].strip()]
            i += 1
            while i < len(lines):
                l = lines[i].strip()
                if _is_any_marker(l):
                    break
                if l and not _is_noise(l):
                    prompt_lines.append(l)
                i += 1
            prompt = "\n".join(prompt_lines).strip()
            if prompt and not prompt.startswith("/"):
                messages.append({"role": "user", "type": "text", "content": prompt})
            continue

        # ── Assistant block ──
        marker = _starts_with_assistant(stripped)
        if marker:
            flush()
            text = stripped[len(marker):].strip()

            if not text or _is_noise(text):
                i += 1
                continue

            if _is_tool(text):
                tool_name = _extract_tool_name(text)
                full_text = text
                i += 1
                while i < len(lines):
                    l = lines[i].strip()
                    if _starts_with_assistant(l) or _is_user_prompt(l) or _starts_with_result(l):
                        break
                    if _is_noise(l):
                        i += 1
                        continue
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

        # ── Tool result ──
        result_marker = _starts_with_result(stripped)
        if result_marker:
            flush()
            result_text = stripped[len(result_marker):].strip()
            i += 1
            while i < len(lines):
                l = lines[i].strip()
                if _starts_with_assistant(l) or _is_user_prompt(l):
                    break
                rm = _starts_with_result(l)
                if rm:
                    result_text += "\n" + l[len(rm):].strip()
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
    return _deduplicate(messages)


def _deduplicate(messages: list[dict]) -> list[dict]:
    """Remove echo and redundant messages."""
    result = []
    for i, msg in enumerate(messages):
        # Skip assistant text that echoes the previous user message
        if (msg["role"] == "assistant" and msg["type"] == "text"
                and result
                and result[-1]["role"] == "user" and result[-1]["type"] == "text"
                and _normalize_text(msg["content"]) == _normalize_text(result[-1]["content"])):
            continue

        # Skip assistant text when next message is TTS tool_use with same content
        if (msg["role"] == "assistant" and msg["type"] == "text"
                and i + 1 < len(messages)
                and messages[i + 1].get("type") == "tool_use"
                and messages[i + 1].get("tool_name") == "tts"):
            tts_text = _extract_tts_plain(messages[i + 1]["content"])
            if _normalize_text(tts_text) == _normalize_text(msg["content"]):
                continue

        result.append(msg)
    return result


def _normalize_text(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _extract_tts_plain(content: str) -> str:
    """Extract the spoken text from TTS tool_use content."""
    m = re.search(r'text:\s*"((?:[^"\\]|\\.)*)"\s*', content)
    if m:
        return m.group(1).replace("\\n", "\n").replace('\\"', '"')
    return content
