from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки сервиса скоринга. Переменные окружения начинаются с SCORING_."""

    model_config = SettingsConfigDict(env_prefix="SCORING_", env_file=".env", extra="ignore")

    # Папка с products.yaml и scorecard.yaml. Можно подменить, не пересобирая образ
    rules_dir: Path = Path(__file__).resolve().parent.parent / "rules"


settings = Settings()
