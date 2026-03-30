FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/root \
    PORT=8924

# System packages + tmux
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    git \
    tmux \
    ca-certificates \
    locales \
    && locale-gen en_US.UTF-8 ru_RU.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

# Node.js 22 + agent CLIs
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update && apt-get install -y nodejs \
    && npm install -g @openai/codex @qwen-code/qwen-code mcp-remote \
    && rm -rf /var/lib/apt/lists/*

# Claude CLI
RUN curl -fsSL https://claude.ai/install.sh | bash
RUN cp -a /root/.claude /root/.claude-default

# Non-root user (ubuntu already exists with uid=1000 — rename)
RUN usermod -l agent -d /home/agent -m ubuntu && groupmod -n agent ubuntu
RUN cp "$(readlink -f /root/.local/bin/claude)" /usr/local/bin/claude

ENV PATH="/usr/local/bin:${PATH}" \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    CODEX_HOME=/home/agent/.codex

WORKDIR /app

# Backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --break-system-packages -r /app/backend/requirements.txt

# Frontend build
COPY frontend/package.json frontend/package-lock.json /app/frontend/
RUN cd /app/frontend && npm ci

COPY frontend/ /app/frontend/
RUN cd /app/frontend && npx nuxi generate

# Backend code
COPY backend/ /app/backend/

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8924

CMD ["/app/entrypoint.sh"]
