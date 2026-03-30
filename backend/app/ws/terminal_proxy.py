import asyncio
import fcntl
import json as json_mod
import os
import pty
import select
import struct
import subprocess
import termios

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import TTS_URL_RE
from app.core.security import verify_token
from app.core.tmux import session_name, validate_id
from app.core.tts import broadcast_tts_url, played_tts_urls

router = APIRouter()


@router.websocket("/ws/terminal/{session_id}")
async def ws_terminal(ws: WebSocket, session_id: str, token: str = Query("")):
    """Connect xterm.js to a tmux session via PTY."""
    payload = verify_token(token)
    if not payload:
        await ws.close(code=4001, reason="Unauthorized")
        return

    validate_id(session_id)
    name = session_name(session_id)

    check_proc = subprocess.run(["tmux", "has-session", "-t", name], capture_output=True)
    if check_proc.returncode != 0:
        await ws.close(code=4004, reason=f"session '{session_id}' not found")
        return

    await ws.accept()

    subprocess.run(["tmux", "set-option", "-t", name, "aggressive-resize", "on"], capture_output=True)
    subprocess.run(["tmux", "set-option", "-t", name, "status", "off"], capture_output=True)

    master_fd, slave_fd = pty.openpty()

    # Wait for initial resize from client
    cols, rows = 120, 40
    try:
        msg = await asyncio.wait_for(ws.receive_text(), timeout=3.0)
        if msg.startswith('{"type":"resize"'):
            data = json_mod.loads(msg)
            cols = data.get("cols", 120)
            rows = data.get("rows", 40)
    except (asyncio.TimeoutError, Exception):
        pass

    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    proc = subprocess.Popen(
        ["tmux", "attach-session", "-d", "-t", name],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
        env={**os.environ, "TERM": "xterm-256color"},
    )
    os.close(slave_fd)

    loop = asyncio.get_event_loop()

    async def read_pty():
        """Read PTY output, intercept TTS URLs, send to WebSocket."""
        try:
            while True:
                readable = loop.create_future()
                loop.add_reader(master_fd, readable.set_result, None)
                try:
                    await readable
                finally:
                    loop.remove_reader(master_fd)

                await asyncio.sleep(0.005)  # coalesce small chunks

                data = b""
                while select.select([master_fd], [], [], 0)[0]:
                    try:
                        chunk = os.read(master_fd, 65536)
                        if not chunk:
                            if data:
                                await ws.send_bytes(data)
                            return
                        data += chunk
                    except OSError:
                        if data:
                            await ws.send_bytes(data)
                        return

                if data:
                    text = data.decode("utf-8", errors="ignore")
                    for url in TTS_URL_RE.findall(text):
                        if url not in played_tts_urls:
                            played_tts_urls.add(url)
                            await broadcast_tts_url(url)
                    await ws.send_bytes(data)
        except (WebSocketDisconnect, asyncio.CancelledError, Exception):
            pass

    async def write_pty():
        """Read WebSocket input, handle resize, write to PTY."""
        try:
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break

                if "text" in msg:
                    text = msg["text"]
                    if text.startswith('{"type":"resize"'):
                        data = json_mod.loads(text)
                        c = data.get("cols", 80)
                        r = data.get("rows", 24)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", r, c, 0, 0))
                    else:
                        os.write(master_fd, text.encode())
                elif "bytes" in msg:
                    os.write(master_fd, msg["bytes"])
        except (WebSocketDisconnect, asyncio.CancelledError, Exception):
            pass

    try:
        await asyncio.gather(read_pty(), write_pty())
    except asyncio.CancelledError:
        pass
    finally:
        proc.terminate()
        try:
            os.close(master_fd)
        except OSError:
            pass
