import asyncio
import re
import subprocess

from fastapi import HTTPException

from app.core.config import CLI, CLI_READY_MARKERS, SESSION_PREFIX, STARTUP_TIMEOUT


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def tmux(*args: str) -> subprocess.CompletedProcess:
    return run_cmd(["tmux", *args])


def session_name(session_id: str) -> str:
    return f"{SESSION_PREFIX}-{session_id}"


def session_target(session_id: str) -> str:
    return f"{session_name(session_id)}:0.0"


def get_pane_output(session_id: str, lines: int = 20) -> str:
    proc = tmux("capture-pane", "-p", "-t", session_target(session_id), "-S", f"-{lines}")
    return proc.stdout if proc.returncode == 0 else ""


def validate_id(session_id: str) -> None:
    if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
        raise HTTPException(
            status_code=400,
            detail="session_id must be alphanumeric, dash, or underscore",
        )


def require_session(session_id: str) -> None:
    validate_id(session_id)
    name = session_name(session_id)
    proc = tmux("has-session", "-t", name)
    if proc.returncode != 0:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found")


async def wait_for_ready(session_id: str, cli: CLI) -> bool:
    markers = CLI_READY_MARKERS[cli]
    for _ in range(STARTUP_TIMEOUT * 2):
        output = get_pane_output(session_id, lines=40)
        if any(m in output for m in markers):
            return True
        await asyncio.sleep(1)
    return False


def list_sessions() -> list[str]:
    """List active tmux sessions matching the agent prefix."""
    proc = tmux("list-sessions", "-F", "#{session_name}")
    if proc.returncode != 0:
        return []
    return [
        s.removeprefix(f"{SESSION_PREFIX}-")
        for s in proc.stdout.strip().splitlines()
        if s.startswith(f"{SESSION_PREFIX}-")
    ]
