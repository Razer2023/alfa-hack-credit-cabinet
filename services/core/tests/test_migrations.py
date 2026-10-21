"""Миграции применяются на чистую БД и совпадают с моделями (никто не забыл сгенерировать миграцию)."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.db import Base

ROOT = Path(__file__).resolve().parents[1]


def test_migrations_match_models(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}")
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert diff == []
