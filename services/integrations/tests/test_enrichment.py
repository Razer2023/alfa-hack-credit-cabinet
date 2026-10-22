from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "integrations.yaml"

BKI = {
    "7701234567": {"max_overdue_days": 0, "active_loans": 1, "total_debt": 400_000},
    "7702345678": {"max_overdue_days": 0, "active_loans": 2, "total_debt": 3_500_000},
    "7703456789": {"max_overdue_days": 45, "active_loans": 3, "total_debt": 6_000_000},
}


def payload(inn: str) -> dict:
    return {
        "application_id": "11111111-1111-1111-1111-111111111111",
        "inn": inn,
        "application": {
            "product_code": "EXPRESS",
            "amount": 2_000_000,
            "term_months": 12,
            "purpose": "Закупка товара",
        },
        "company": {"name": "Демо", "revenue_year": 1},
        "extra": {},
    }


def test_demo_companies_have_stub_bki_and_registers():
    for inn, bki in BKI.items():
        body = client.post("/api/v1/checks", json=payload(inn)).json()
        assert body["complete"] is True
        assert body["enrichment"]["bki"] == bki
        assert body["enrichment"]["egrul"] == {"status": "ACTIVE", "liquidation": False}
        assert body["enrichment"]["fns"] == {"tax_debt": 0, "mass_address": False}


def test_unknown_inn_gets_empty_credit_history():
    body = client.post("/api/v1/checks", json=payload("7700000000")).json()
    assert body["complete"] is True
    assert body["enrichment"]["bki"] == {"max_overdue_days": 0, "active_loans": 0, "total_debt": 0}


def test_contract_names_bki_fields():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "max_overdue_days" in text
    assert "mass_address" in text
