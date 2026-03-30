#!/usr/bin/env bash
set -e

AGENT_HOME=/home/agent

mkdir -p "$AGENT_HOME/.claude" "$AGENT_HOME/.codex"

# Merge default Claude installer files into mounted config directory
if [ -d /root/.claude-default ]; then
    cp -rn /root/.claude-default/. "$AGENT_HOME/.claude/" 2>/dev/null || true
fi

# Persist .claude.json via symlink into mounted volume
SAVED="$AGENT_HOME/.claude/.root-claude.json"
if [ -f "$AGENT_HOME/.claude.json" ] && [ ! -L "$AGENT_HOME/.claude.json" ]; then
    mv "$AGENT_HOME/.claude.json" "$SAVED"
    ln -sf "$SAVED" "$AGENT_HOME/.claude.json"
elif [ ! -e "$AGENT_HOME/.claude.json" ] && [ -f "$SAVED" ]; then
    ln -sf "$SAVED" "$AGENT_HOME/.claude.json"
fi

chown -R agent:agent "$AGENT_HOME" 2>/dev/null || true

# Ensure data directory is writable for SQLite
mkdir -p /data
chown agent:agent /data

exec runuser -u agent -- bash -c '
    tmux kill-server 2>/dev/null || true
    tmux start-server
    export WATCHFILES_FORCE_POLLING=true
    cd /app/backend
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --reload --reload-dir /app/backend/app
'
