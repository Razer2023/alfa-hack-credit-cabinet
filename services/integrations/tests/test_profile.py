from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DEMO = {
    "7701234567": ("ООО «Кофейня на Лесной»", 24_000_000, 2_000_000),
    "7702345678": ("ООО «СтройМонтаж»", 30_000_000, 2_500_000),
    "7703456789": ("ООО «Вектор Трейд»", 18_000_000, 1_500_000),
}

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "integrations.yaml"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_demo_profiles_match_stub():
    for inn, (name, revenue, turnover) in DEMO.items():
        body = client.get(f"/api/v1/companies/{inn}/profile").json()
        assert body["inn"] == inn
        assert body["fields"]["name"] == {"value": name, "source": "EGRUL"}
        assert body["fields"]["revenue_year"] == {"value": revenue, "source": "BANK_ACCOUNT"}
        assert body["fields"]["avg_monthly_turnover"] == {"value": turnover, "source": "BANK_ACCOUNT"}
        assert body["fields"]["employees"]["source"] == "FNS"
        assert isinstance(body["fields"]["employees"]["value"], int)


def test_unknown_inn_is_404():
    response = client.get("/api/v1/companies/7700000000/profile")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_contract_describes_profile_and_health():
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    profile = spec["paths"]["/api/v1/companies/{inn}/profile"]["get"]
    assert "200" in profile["responses"]
    assert "404" in profile["responses"]
    assert "EGRUL" in str(spec)
    health = spec["paths"]["/health"]["get"]
    assert "200" in health["responses"]
