-include .env
export

IMAGE_NAME    = agentbox
PORT          = 8924
WORKSPACE    ?= $(HOME)/projects/workspace
CLAUDE_CONFIG ?= $(HOME)/.claude-agent
CODEX_CONFIG  ?= $(HOME)/.codex-agent
QWEN_CONFIG   ?= $(HOME)/.qwen-agent

.PHONY: build run start stop restart rebuild health logs attach dev

build:
	docker build --network host -t $(IMAGE_NAME) .

run:
	@mkdir -p "$(CLAUDE_CONFIG)" "$(CODEX_CONFIG)" "$(QWEN_CONFIG)"
	docker run --rm -it \
		--network host \
		--hostname $(IMAGE_NAME) \
		-e AUTH_LOGIN=$(AUTH_LOGIN) \
		-e AUTH_PASSWORD=$(AUTH_PASSWORD) \
		-e SECRET_KEY=$(SECRET_KEY) \
		-e ASR_TOKEN=$(ASR_TOKEN) \
		-e ASR_NORMALIZE=$(ASR_NORMALIZE) \
		-e MIND_API_KEY=$(MIND_API_KEY) \
		-e TTS_VOICE=$(TTS_VOICE) \
		\
		-v agentbox-data:/data \
		-v "$(WORKSPACE):/workspace" \
		-v "$(CLAUDE_CONFIG):/home/agent/.claude" \
		-v "$(CODEX_CONFIG):/home/agent/.codex" \
		-v "$(QWEN_CONFIG):/home/agent/.qwen" \
		-v "$(CURDIR)/backend/app:/app/backend/app" \
		-v "$(CURDIR)/entrypoint.sh:/app/entrypoint.sh" \
		--name $(IMAGE_NAME) \
		$(IMAGE_NAME)

start:
	@mkdir -p "$(CLAUDE_CONFIG)" "$(CODEX_CONFIG)" "$(QWEN_CONFIG)"
	docker run -d \
		--network host \
		--restart unless-stopped \
		--hostname $(IMAGE_NAME) \
		-e AUTH_LOGIN=$(AUTH_LOGIN) \
		-e AUTH_PASSWORD=$(AUTH_PASSWORD) \
		-e SECRET_KEY=$(SECRET_KEY) \
		-e ASR_TOKEN=$(ASR_TOKEN) \
		-e ASR_NORMALIZE=$(ASR_NORMALIZE) \
		-e MIND_API_KEY=$(MIND_API_KEY) \
		-e TTS_VOICE=$(TTS_VOICE) \
		\
		-v agentbox-data:/data \
		-v "$(WORKSPACE):/workspace" \
		-v "$(CLAUDE_CONFIG):/home/agent/.claude" \
		-v "$(CODEX_CONFIG):/home/agent/.codex" \
		-v "$(QWEN_CONFIG):/home/agent/.qwen" \
		-v "$(CURDIR)/backend/app:/app/backend/app" \
		-v "$(CURDIR)/entrypoint.sh:/app/entrypoint.sh" \
		--name $(IMAGE_NAME) \
		$(IMAGE_NAME)

rebuild: stop build start

attach:
	docker exec -it -u agent $(IMAGE_NAME) tmux attach

stop:
	docker stop $(IMAGE_NAME) 2>/dev/null || true
	docker rm $(IMAGE_NAME) 2>/dev/null || true

restart:
	docker restart $(IMAGE_NAME)

health:
	curl -s http://localhost:$(PORT)/api/health | python3 -m json.tool

logs:
	docker logs -f $(IMAGE_NAME)

dev:
	@echo "Starting backend (port $(PORT)) and frontend (port 3005)..."
	@cd backend && uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload &
	@cd frontend && npm run dev
