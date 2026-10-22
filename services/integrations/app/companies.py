"""Синтетические профили компаний.

Источник — data/synthetic/companies.json (область B). Те же три демо-ИНН, что во встроенной
заглушке ядра: на них держится демо-сценарий.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

SOURCES = frozenset({"EGRUL", "FNS", "BANK_ACCOUNT"})


def companies_path() -> Path:
    override = os.environ.get("INTEGRATIONS_COMPANIES_PATH")
    if override:
        return Path(override)
    repo = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "companies.json"
    if repo.is_file():
        return repo
    return Path("/app/data/synthetic/companies.json")


@lru_cache(maxsize=1)
def load_companies() -> dict[str, dict]:
    path = companies_path()
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict) or not data:
        raise ValueError(f"В {path} нет профилей компаний")
    return data


def company_profile(inn: str) -> dict | None:
    company = load_companies().get(inn)
    if company is None:
        return None
    return {"inn": inn, "fields": company}
