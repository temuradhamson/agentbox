from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AGENT_BOX_URL: str = "http://localhost:8922"
    # CHATCAP removed — parsing built-in
    SECRET_KEY: str = "agent-hub-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    HOST: str = "0.0.0.0"
    PORT: int = 8924

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
