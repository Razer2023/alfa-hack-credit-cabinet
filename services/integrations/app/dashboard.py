"""Синтетический массив заявок для дашборда узких мест.

Живой дашборд (S8.1) строит область A из журнала событий ядра.
Здесь заранее посчитанные длительности этапов, чтобы график было на чём показать,
пока в журнале только три демо-заявки.
"""

import json
import os
from functools import lru_cache
from pathlib import Path


def dashboard_path() -> Path:
    override = os.environ.get("INTEGRATIONS_DASHBOARD_PATH")
    if override:
        return Path(override)
    repo = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "dashboard.json"
    if repo.is_file():
        return repo
    return Path("/app/data/synthetic/dashboard.json")


@lru_cache(maxsize=1)
def load_dashboard() -> list[dict]:
    path = dashboard_path()
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list) or not data:
        raise ValueError(f"В {path} нет заявок для дашборда")
    return data
