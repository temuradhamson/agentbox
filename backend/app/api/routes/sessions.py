import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import CLI, CLI_COMMANDS, CLI_RESUME_INPUT, settings
from app.core.parser import parse_terminal_output
from app.core.tmux import (
    get_pane_output,
    list_sessions as tmux_list_sessions,
    require_session,
    session_name,
    session_target,
    tmux,
    validate_id,
    wait_for_ready,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"], dependencies=[Depends(get_current_user)])

# In-memory tracking for timestamps
_msg_counts: dict[str, int] = {}
_msg_timestamps: dict[str, dict[int, str]] = {}


class CreateSession(BaseModel):
    session_id: str
    workdir: str = "/workspace"
    cli: CLI = CLI.claude
    resume: bool = False


class SendRequest(BaseModel):
    text: str


@router.get("")
async def list_sessions_endpoint():
    ids = tmux_list_sessions()
    return {"sessions": [{"id": sid} for sid in ids]}


@router.post("")
async def create_session_endpoint(body: CreateSession):
    validate_id(body.session_id)
    name = session_name(body.session_id)

    check = tmux("has-session", "-t", name)
    if check.returncode == 0:
        raise HTTPException(status_code=409, detail=f"session '{body.session_id}' already exists")

    proc = tmux("new-session", "-d", "-s", name, "-c", body.workdir)
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr.strip() or "failed to create session")

    target = session_target(body.session_id)
    tmux("send-keys", "-t", target, "-l", "--", CLI_COMMANDS[body.cli])
    tmux("send-keys", "-t", target, "Enter")

    ready = await wait_for_ready(body.session_id, body.cli)

    # Auto-send /resume if requested (only after CLI is ready)
    if body.resume and ready and body.cli in CLI_RESUME_INPUT:
        resume_cmd = CLI_RESUME_INPUT[body.cli]
        tmux("send-keys", "-t", target, "-l", "--", resume_cmd)
        time.sleep(settings.SEND_ENTER_DELAY)
        tmux("send-keys", "-t", target, "Enter")

    return {
        "ok": True,
        "session_id": body.session_id,
        "cli": body.cli.value,
        "status": "ready" if ready else "starting",
        "resumed": body.resume,
    }


@router.get("/{session_id}/messages")
async def get_messages_endpoint(session_id: str):
    try:
        output = get_pane_output(session_id, lines=500)
    except Exception:
        return {"messages": []}

    if not output:
        return {"messages": []}

    msgs = parse_terminal_output(output)

    now = datetime.now(timezone.utc).isoformat()
    prev_count = _msg_counts.get(session_id, 0)
    cur_count = len(msgs)

    if session_id not in _msg_timestamps:
        _msg_timestamps[session_id] = {}

    if cur_count > prev_count:
        for idx in range(prev_count, cur_count):
            _msg_timestamps[session_id][idx] = now
        _msg_counts[session_id] = cur_count

    ts_map = _msg_timestamps.get(session_id, {})
    for idx, msg in enumerate(msgs):
        if idx in ts_map:
            msg["timestamp"] = ts_map[idx]

    return {"messages": msgs}


@router.get("/{session_id}/tail")
def tail(session_id: str, lines: int = 80):
    require_session(session_id)
    proc = tmux("capture-pane", "-p", "-t", session_target(session_id), "-S", f"-{lines}")
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr.strip() or "capture failed")
    return {"session_id": session_id, "output": proc.stdout}


@router.delete("/{session_id}")
def delete_session_endpoint(session_id: str):
    tmux("kill-session", "-t", session_name(session_id))
    _msg_counts.pop(session_id, None)
    _msg_timestamps.pop(session_id, None)
    return {"ok": True, "session_id": session_id}


@router.post("/{session_id}/send")
def send(session_id: str, payload: SendRequest):
    require_session(session_id)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")

    target = session_target(session_id)

    send_text = tmux("send-keys", "-t", target, "-l", "--", text)
    if send_text.returncode != 0:
        raise HTTPException(status_code=500, detail=send_text.stderr.strip() or "send text failed")

    time.sleep(settings.SEND_ENTER_DELAY)

    send_enter = tmux("send-keys", "-t", target, "Enter")
    if send_enter.returncode != 0:
        raise HTTPException(status_code=500, detail=send_enter.stderr.strip() or "send enter failed")

    return {"ok": True, "session_id": session_id, "sent": text}


@router.post("/{session_id}/interrupt")
def interrupt(session_id: str):
    require_session(session_id)
    tmux("send-keys", "-t", session_target(session_id), "C-c")
    return {"ok": True, "session_id": session_id}
