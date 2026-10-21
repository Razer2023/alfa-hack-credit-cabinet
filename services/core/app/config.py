from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки ядра. Все переменные окружения начинаются с CORE_ (см. .env.example)."""

    model_config = SettingsConfigDict(env_prefix="CORE_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./core.db"

    jwt_secret: str = "dev-only-secret-change-me-in-production-0123456789"
    jwt_ttl_minutes: int = 480
    demo_password: str = "demo"

    # stub — встроенные заглушки до готовности сервисов B и C; http — вызов настоящих сервисов
    integrations_mode: str = "stub"
    integrations_url: str = "http://integrations:8000"
    scoring_mode: str = "stub"
    scoring_url: str = "http://scoring:8000"
    external_timeout_seconds: float = 5.0

    # Фоновый обработчик заявок (CHECKING → SCORING → решение, выдача)
    worker_enabled: bool = True
    worker_poll_seconds: float = 1.0
    # Пауза перед каждым автоматическим шагом, чтобы на демо было видно движение статусов
    pipeline_step_delay_seconds: float = 2.0

    # Код подтверждения (мок ПЭП). SMS запрещены условиями кейса, поэтому в демо код возвращается в ответе API
    demo_codes: bool = True
    code_ttl_seconds: int = 300
    code_max_attempts: int = 5

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
