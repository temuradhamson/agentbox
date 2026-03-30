import re
from enum import Enum

from pydantic_settings import BaseSettings


class CLI(str, Enum):
    claude = "claude"
    codex = "codex"
    qwen = "qwen"


CLI_COMMANDS: dict[CLI, str] = {
    CLI.claude: "claude --dangerously-skip-permissions",
    CLI.codex: "codex --ask-for-approval never --sandbox danger-full-access",
    CLI.qwen: "qwen --yolo",
}

# Text sent INTO the CLI after it's ready to trigger its built-in resume
CLI_RESUME_INPUT: dict[CLI, str] = {
    CLI.claude: "/resume",
    CLI.codex: "/resume",
    CLI.qwen: "/resume",
}

CLI_READY_MARKERS: dict[CLI, list[str]] = {
    CLI.claude: [">", "\u276f"],
    CLI.codex: [">", "\u276f"],
    CLI.qwen: [">", "\u276f"],
}

TTS_URL_RE = re.compile(r"https://whisper-asr\.2dox\.uz/static/\S+?\.wav")

SESSION_PREFIX = "agent"
STARTUP_TIMEOUT = 30


class Settings(BaseSettings):
    # Auth
    SECRET_KEY: str = "agent-hub-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    AUTH_LOGIN: str = "admin"
    AUTH_PASSWORD: str = ""

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8924

    # Tmux
    SEND_ENTER_DELAY: float = 0.2

    # ASR
    ASR_API_URL: str = "https://whisper-asr.2dox.uz/qwen/transcribe"
    ASR_TOKEN: str = ""
    ASR_LANGUAGE: str = "ru"
    ASR_NORMALIZE: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
