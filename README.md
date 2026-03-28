# Agent Hub

Real-time web interface for AI coding agents (Claude Code, Codex, Qwen Code) running inside [AI Agent Box](https://github.com/Yakvenalex/LLMConsoleProject) Docker container.

**Agent Hub** is a standalone frontend that connects to Agent Box and provides:
- Chat mode with structured messages (parsed from terminal output)
- Terminal mode with xterm.js
- TTS auto-playback with Telegram-style audio player
- Voice input via ASR
- Session management

## Architecture

```
Browser (Agent Hub frontend, Nuxt 3)
  |
  |-- REST /api/* --> Agent Hub backend (FastAPI) --> Agent Box (Docker)
  |-- WS /ws/terminal/* --> Agent Hub backend --> Agent Box /ws/terminal/*
  |-- WS direct --> Agent Box /ws/tts (TTS audio stream)
```

Agent Hub **does not modify** Agent Box. It connects to it via HTTP API and WebSocket as a client.

## Prerequisites

**[AI Agent Box](https://github.com/Yakvenalex/LLMConsoleProject)** must be running. Follow its README to set up:

```bash
# Clone Alexey's project
git clone https://github.com/Yakvenalex/LLMConsoleProject.git
cd LLMConsoleProject

# Configure
cp .env.example .env
# Edit .env: set WORKSPACE, API keys, AUTH_LOGIN, AUTH_PASSWORD, etc.

# Build and start (requires Docker + WSL on Windows)
make build
make start

# Verify it's running
curl http://localhost:8922/health
```

Default Agent Box port: **8922** (configurable via `PORT` in `.env`).

## Setup Agent Hub

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\pip install -r requirements.txt

# Linux/Mac
venv/bin/pip install -r requirements.txt

# Configure
cp .env.example .env
```

Edit `backend/.env`:

```env
AGENT_BOX_URL=http://localhost:8922   # Agent Box address
SECRET_KEY=your-random-secret-here    # JWT secret (any random string)
AB_LOGIN=admin                        # Same as AUTH_LOGIN in Agent Box .env
AB_PASSWORD=admin123                  # Same as AUTH_PASSWORD in Agent Box .env
```

**Important:** `AB_LOGIN` and `AB_PASSWORD` must match Agent Box's `AUTH_LOGIN` and `AUTH_PASSWORD`.

Start the backend:

```bash
# Windows
venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8924

# Linux/Mac
venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8924
```

### 2. Frontend

```bash
cd frontend
npm install
npx nuxi dev --port 3005
```

Open **http://localhost:3005** and login with Agent Box credentials.

## Connecting to Agent Box

Agent Hub connects to Agent Box via three channels:

| Channel | Direction | Purpose |
|---------|-----------|---------|
| REST API (via backend proxy) | Hub --> Agent Box | Session CRUD, send text, ASR, tail output |
| Terminal WebSocket (via backend proxy) | Hub <--> Agent Box | xterm.js live terminal |
| TTS WebSocket (direct from browser) | Hub <-- Agent Box | Real-time audio playback |

### How it works

1. **Login**: Agent Hub backend authenticates with Agent Box using `AB_LOGIN`/`AB_PASSWORD` and caches the token
2. **Sessions**: Lists/creates/deletes sessions via Agent Box `/sessions` API
3. **Chat mode**: Fetches terminal output via `/sessions/{id}/tail`, parses markers (`❯` = user, `●` = assistant, `⎿` = tool result) into structured messages
4. **Terminal mode**: Bidirectional WebSocket proxy to Agent Box terminal
5. **TTS**: Browser connects directly to Agent Box `/ws/tts` for zero-latency audio playback
6. **ASR**: Audio recording sent through backend proxy to Agent Box `/asr` endpoint

### Agent Box TTS setup

For voice output to work, the agent inside Agent Box needs a TTS MCP server configured. See Agent Box README for details on:
- Setting `TTS_VOICE` in `.env` (e.g., `kseniya`, `aidar`)
- Copying TTS instruction files (`CLAUDE.md`, `AGENTS.md`, `QWEN.md`) to your workspace

## Port Summary

| Service | Port | Description |
|---------|------|-------------|
| Agent Box | 8922 | Docker container with AI agent terminals |
| Agent Hub backend | 8924 | FastAPI proxy + parser |
| Agent Hub frontend | 3005 | Nuxt 3 dev server |

## Features

- **Two view modes**: Chat (structured messages) / Terminal (xterm.js)
- **TTS auto-play**: Preloading queue, Auto/Mute toggle
- **Voice input**: Record + transcribe + send to agent
- **Audio player**: Telegram-style waveform, seek, play/pause
- **Terminal toolbar**: Ctrl+C, Ctrl+D, Ctrl+Z, Esc, Tab, Shift+Tab, arrows
- **Timestamps**: Real-time on new messages, day grouping
- **Session management**: Create, switch, delete, activity tracking
- **Preferences**: Mode, sidebar state, active session saved in localStorage
- **Noise filtering**: Parser strips terminal UI artifacts (decorative lines, bypass prompts, etc.)

## Tech Stack

- **Frontend**: Nuxt 3, Vue 3, Tailwind CSS 3, Pinia, xterm.js
- **Backend**: FastAPI, httpx, websockets, python-jose
- **Agent Box**: [Yakvenalex/LLMConsoleProject](https://github.com/Yakvenalex/LLMConsoleProject) (FastAPI + tmux + Docker)

## License

MIT
