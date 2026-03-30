# Agent Box

Полностью автономный веб-интерфейс для AI-агентов (Claude Code, Codex, Qwen Code) в Docker-контейнере. Единый бэкенд (FastAPI) + единый фронтенд (Nuxt 3) + Docker.

## Возможности

- **Два режима**: Чат (структурированные сообщения) / Терминал (xterm.js)
- **Три CLI**: Claude Code, OpenAI Codex, Qwen Code — с переключением при создании сессии
- **Resume**: переключатель в форме создания — CLI автоматически открывает список предыдущих сессий
- **Автоозвучка TTS**: очередь с предзагрузкой, переключатель Auto/Mute, кнопка Stop в терминале
- **Голосовой ввод**: запись + транскрибация (ASR) + отправка агенту
- **Аудиоплеер**: стиль Telegram — волноформа, перемотка, play/pause, длительность
- **Панель терминала**: Ctrl+C/D/Z, Esc, Tab, Shift+Tab, стрелки, микрофон
- **Универсальный парсер**: поддержка маркеров Claude (`●`/`⎿`/`❯`), Codex (`•`/`└`/`›`), Qwen (`✦`/`└`/`>`)
- **Фильтрация шума**: ANSI-коды, thinking-статусы, декоративные линии, UI-промпты

## Архитектура

```
Браузер (Nuxt 3 SPA)
  │
  ├── REST /api/*        ──→ FastAPI ──→ tmux (напрямую)
  ├── WS /ws/terminal/*  ──→ FastAPI ──→ PTY ↔ tmux session
  └── WS /ws/tts         ──→ FastAPI ──→ TTS broadcast
                                │
                          tmux sessions
                          ├── claude --dangerously-skip-permissions
                          ├── codex --ask-for-approval never
                          └── qwen --yolo
```

Всё работает в **одном контейнере** через один порт (8924). Нет прокси-слоя — бэкенд управляет tmux напрямую.

## Быстрый старт (Docker)

```bash
# Клонировать
git clone https://github.com/temuradhamson/agentbox.git
cd agentbox

# Настроить
cp .env.example .env
# Отредактировать .env: пути, API-ключи, пароль

# Собрать и запустить
make build
make start

# Проверить
make health
```

Открыть **http://localhost:8924** — логин с AUTH_LOGIN/AUTH_PASSWORD из `.env`.

## Конфигурация (.env)

```env
# Пути (монтируются в контейнер)
WORKSPACE=/home/user/projects/my-workspace
CLAUDE_CONFIG=/home/user/.claude-agent
CODEX_CONFIG=/home/user/.codex-agent
QWEN_CONFIG=/home/user/.qwen-agent

# API-ключи
MIND_API_KEY=your-api-key        # Для Qwen
ASR_TOKEN=your-asr-token         # Для распознавания речи

# TTS голос (kseniya, aidar, xenia, eugene, baya)
TTS_VOICE=aidar

# Авторизация
AUTH_LOGIN=admin
AUTH_PASSWORD=your-password
SECRET_KEY=your-random-secret-key
```

## Makefile команды

| Команда | Описание |
|---------|----------|
| `make build` | Собрать Docker-образ |
| `make start` | Запустить в фоне (daemon) |
| `make run` | Запустить интерактивно (-it --rm) |
| `make stop` | Остановить и удалить контейнер |
| `make rebuild` | stop + build + start |
| `make attach` | Подключиться к tmux внутри контейнера |
| `make health` | Проверить /api/health |
| `make logs` | Просмотр логов |
| `make dev` | Локальная разработка (бэк + фронт) |

## Локальная разработка (без Docker)

```bash
# Бэкенд
cd backend
pip install -r requirements.txt
cp .env.example .env  # настроить
uvicorn app.main:app --host 0.0.0.0 --port 8924 --reload

# Фронтенд (в другом терминале)
cd frontend
npm install
npm run dev  # http://localhost:3005
```

Nuxt dev-сервер проксирует `/api/*` и `/ws/*` на бэкенд (порт 8924).

## Настройка TTS (озвучка)

Для работы голосового вывода агенту нужен TTS MCP-сервер. Скопируйте файлы из `examples/`:

```bash
# Claude Code
cp examples/CLAUDE_EXAMPLE.md $WORKSPACE/CLAUDE.md
cp examples/.mcp.json.example $WORKSPACE/.mcp.json

# Codex
cp examples/AGENTS_EXAMPLE.md $WORKSPACE/AGENTS.md
cp examples/codex.config.toml.example $WORKSPACE/.codex/config.toml

# Qwen Code
cp examples/QWEN_EXAMPLE.md $WORKSPACE/QWEN.md
cp examples/qwen.settings.json.example $WORKSPACE/.qwen/settings.json
```

## Стек технологий

- **Фронтенд**: Nuxt 3, Vue 3, Tailwind CSS, Pinia, xterm.js
- **Бэкенд**: FastAPI, python-jose (JWT), httpx (ASR)
- **Контейнер**: Ubuntu 24.04, tmux, Node.js 22, Python 3
- **CLI**: Claude Code, OpenAI Codex, Qwen Code

## Лицензия

MIT
