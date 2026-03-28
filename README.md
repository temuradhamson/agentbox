# Agent Hub

Веб-интерфейс реального времени для AI-агентов (Claude Code, Codex, Qwen Code), работающих внутри Docker-контейнера [AI Agent Box](https://github.com/Yakvenalex/LLMConsoleProject).

**Agent Hub** — отдельный фронтенд, который подключается к Agent Box и предоставляет:
- Режим чата со структурированными сообщениями (парсинг терминального вывода)
- Режим терминала с xterm.js
- Автовоспроизведение TTS с аудиоплеером в стиле Telegram
- Голосовой ввод через ASR
- Управление сессиями

## Архитектура

```
Браузер (Agent Hub frontend, Nuxt 3)
  |
  |-- REST /api/* --> Agent Hub backend (FastAPI) --> Agent Box (Docker)
  |-- WS /ws/terminal/* --> Agent Hub backend --> Agent Box /ws/terminal/*
  |-- WS напрямую --> Agent Box /ws/tts (аудиопоток TTS)
```

Agent Hub **не модифицирует** Agent Box. Он подключается к нему по HTTP API и WebSocket как клиент.

## Требования

Должен быть запущен **[AI Agent Box](https://github.com/Yakvenalex/LLMConsoleProject)** (проект Алексея). Установка по его README:

```bash
# Клонировать проект Алексея
git clone https://github.com/Yakvenalex/LLMConsoleProject.git
cd LLMConsoleProject

# Настроить
cp .env.example .env
# Отредактировать .env: WORKSPACE, API-ключи, AUTH_LOGIN, AUTH_PASSWORD и т.д.

# Собрать и запустить (нужен Docker + WSL на Windows)
make build
make start

# Проверить
curl http://localhost:8922/health
```

Порт Agent Box по умолчанию: **8922** (настраивается через `PORT` в `.env`).

## Установка Agent Hub

### 1. Бэкенд

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\pip install -r requirements.txt

# Linux/Mac
venv/bin/pip install -r requirements.txt

# Настроить
cp .env.example .env
```

Отредактировать `backend/.env`:

```env
AGENT_BOX_URL=http://localhost:8922   # Адрес Agent Box
SECRET_KEY=ваш-случайный-секрет      # JWT-секрет (любая случайная строка)
AB_LOGIN=admin                        # Совпадает с AUTH_LOGIN в .env Agent Box
AB_PASSWORD=admin123                  # Совпадает с AUTH_PASSWORD в .env Agent Box
```

**Важно:** `AB_LOGIN` и `AB_PASSWORD` должны совпадать с `AUTH_LOGIN` и `AUTH_PASSWORD` в конфиге Agent Box.

Запустить бэкенд:

```bash
# Windows
venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8924

# Linux/Mac
venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8924
```

### 2. Фронтенд

```bash
cd frontend
npm install
npx nuxi dev --port 3005
```

Открыть **http://localhost:3005** и войти с учётными данными Agent Box.

## Связь с Agent Box

Agent Hub подключается к Agent Box по трём каналам:

| Канал | Направление | Назначение |
|-------|-------------|------------|
| REST API (через прокси бэкенда) | Hub --> Agent Box | CRUD сессий, отправка текста, ASR, tail вывода |
| Terminal WebSocket (через прокси) | Hub <--> Agent Box | Живой терминал xterm.js |
| TTS WebSocket (напрямую из браузера) | Hub <-- Agent Box | Воспроизведение озвучки в реальном времени |

### Как это работает

1. **Логин**: бэкенд Agent Hub аутентифицируется в Agent Box через `AB_LOGIN`/`AB_PASSWORD` и кэширует токен
2. **Сессии**: список/создание/удаление через Agent Box API `/sessions`
3. **Режим чата**: получает вывод терминала через `/sessions/{id}/tail`, парсит маркеры (`❯` = пользователь, `●` = ассистент, `⎿` = результат инструмента) в структурированные сообщения
4. **Режим терминала**: двунаправленный WebSocket-прокси к терминалу Agent Box
5. **TTS**: браузер подключается напрямую к Agent Box `/ws/tts` для воспроизведения без задержек
6. **ASR**: аудиозапись отправляется через прокси бэкенда на Agent Box `/asr`

### Настройка озвучки (TTS)

Для работы голосового вывода агенту внутри Agent Box нужен настроенный TTS MCP-сервер. Подробности в README Agent Box:
- Установить `TTS_VOICE` в `.env` (например, `kseniya`, `aidar`)
- Скопировать файлы инструкций (`CLAUDE.md`, `AGENTS.md`, `QWEN.md`) в workspace

## Порты

| Сервис | Порт | Описание |
|--------|------|----------|
| Agent Box | 8922 | Docker-контейнер с терминалами AI-агентов |
| Agent Hub бэкенд | 8924 | FastAPI прокси + парсер |
| Agent Hub фронтенд | 3005 | Nuxt 3 dev-сервер |

## Возможности

- **Два режима**: Чат (структурированные сообщения) / Терминал (xterm.js)
- **Автоозвучка TTS**: очередь с предзагрузкой, переключатель Auto/Mute
- **Голосовой ввод**: запись + транскрибация + отправка агенту, визуализатор уровня
- **Аудиоплеер**: в стиле Telegram — волноформа, перемотка, play/pause, длительность
- **Панель терминала**: Ctrl+C, Ctrl+D, Ctrl+Z, Esc, Tab, Shift+Tab, стрелки, микрофон
- **Метки времени**: реальное время на новых сообщениях, группировка по дням
- **Управление сессиями**: создание, переключение, удаление, отслеживание активности
- **Сохранение настроек**: режим, сайдбар, активная сессия — всё в localStorage
- **Фильтрация мусора**: парсер убирает артефакты терминала (декоративные линии, bypass-промпты и т.д.)

## Стек технологий

- **Фронтенд**: Nuxt 3, Vue 3, Tailwind CSS 3, Pinia, xterm.js
- **Бэкенд**: FastAPI, httpx, websockets, python-jose
- **Agent Box**: [Yakvenalex/LLMConsoleProject](https://github.com/Yakvenalex/LLMConsoleProject) (FastAPI + tmux + Docker)

## Лицензия

MIT
