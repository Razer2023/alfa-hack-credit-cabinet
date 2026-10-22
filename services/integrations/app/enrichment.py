"""Моки ЕГРЮЛ, ФНС («Прозрачный бизнес») и БКИ (S4.2).

Выписка по счёту уже приходит в профиле компании (S3.1, source BANK_ACCOUNT).
Цифры БКИ те же, что у заглушки ядра: от них зависят три исхода демо.
Неизвестный ИНН получает нулевую историю, как заглушка, и не роняет проверку.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

DEFAULT = {
    "egrul": {"status": "ACTIVE", "liquidation": False},
    "fns": {"tax_debt": 0, "mass_address": False},
    "bki": {"max_overdue_days": 0, "active_loans": 0, "total_debt": 0},
}


def enrichment_path() -> Path:
    override = os.environ.get("INTEGRATIONS_ENRICHMENT_PATH")
    if override:
        return Path(override)
    repo = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "enrichment.json"
    if repo.is_file():
        return repo
    return Path("/app/data/synthetic/enrichment.json")


@lru_cache(maxsize=1)
def load_enrichment() -> dict[str, dict]:
    path = enrichment_path()
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict) or not data:
        raise ValueError(f"В {path} нет данных проверок")
    return data


def enrichment_for(inn: str) -> dict:
    found = load_enrichment().get(inn)
    source = found if found else DEFAULT
    return {key: dict(value) for key, value in source.items()}
