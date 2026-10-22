from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rules import get_rules

TODAY = date(2026, 10, 22)

# Три демо-компании — те же синтетические данные, что у заглушек ядра и сервиса B
COMPANIES = {
    "7701234567": {"registration_date": "2020-03-12", "employees": 12, "revenue_year": 24_000_000, "avg_monthly_turnover": 2_000_000},
    "7702345678": {"registration_date": "2018-06-01", "employees": 35, "revenue_year": 30_000_000, "avg_monthly_turnover": 2_500_000},
    "7703456789": {"registration_date": "2021-09-20", "employees": 9, "revenue_year": 18_000_000, "avg_monthly_turnover": 1_500_000},
}
BKI = {
    "7701234567": {"max_overdue_days": 0, "active_loans": 1, "total_debt": 400_000},
    "7702345678": {"max_overdue_days": 0, "active_loans": 2, "total_debt": 3_500_000},
    "7703456789": {"max_overdue_days": 45, "active_loans": 3, "total_debt": 6_000_000},
}


def make_request(inn: str, product: str, amount: int, term: int, *, company=None, egrul=None, fns=None, bki=None) -> dict:
    """Запрос в формате ядра (services/core/app/pipeline.py: snapshot + enrichment)."""
    return {
        "application_id": "00000000-0000-0000-0000-000000000001",
        "inn": inn,
        "application": {"product_code": product, "amount": amount, "term_months": term, "purpose": "Тест"},
        "company": COMPANIES[inn] | (company or {}),
        "extra": {},
        "enrichment": {
            "egrul": {"status": "ACTIVE", "liquidation": False} | (egrul or {}),
            "fns": {"tax_debt": 0, "mass_address": False} | (fns or {}),
            "bki": BKI[inn] | (bki or {}),
        },
    }


@pytest.fixture
def rules():
    return get_rules()


@pytest.fixture
def api():
    with TestClient(app) as client:
        yield client
