"""Эндпоинты по ТЗ ядра (tz/C-scoring/2026-10-21-a-core-contract.md)."""

from conftest import make_request


def test_health(api):
    body = api.get("/health").json()
    assert body["status"] == "ok" and body["model_version"].startswith("scorecard-")


def test_products(api):
    products = api.get("/api/v1/products").json()
    assert [p["code"] for p in products] == ["EXPRESS", "WORKING_CAPITAL", "INVESTMENT"]
    assert api.get("/api/v1/products/EXPRESS").json()["base_rate"] == 22.5
    assert api.get("/api/v1/products/NOPE").status_code == 404


def test_payment_matches_contract_example(api):
    body = api.post("/api/v1/calc/payment", json={"amount": 1_200_000, "term_months": 12, "rate": 22.5}).json()
    assert body == {"monthly_payment": 112602, "total_payment": 1351224, "overpayment": 151224}


def test_payment_zero_rate(api):
    body = api.post("/api/v1/calc/payment", json={"amount": 1_200_000, "term_months": 12, "rate": 0}).json()
    assert body == {"monthly_payment": 100000, "total_payment": 1_200_000, "overpayment": 0}


def test_payment_validation(api):
    assert api.post("/api/v1/calc/payment", json={"amount": 0, "term_months": 12, "rate": 10}).status_code == 422


def test_decision_shape(api):
    body = api.post("/api/v1/decisions", json=make_request("7701234567", "EXPRESS", 2_000_000, 12)).json()
    assert set(body) >= {"result", "score", "risk_class", "model_version", "factors", "reasons", "offers"}
    assert all(set(f) >= {"code", "title", "impact"} for f in body["factors"])


def test_decision_unknown_product(api):
    response = api.post("/api/v1/decisions", json=make_request("7701234567", "NOPE", 2_000_000, 12))
    assert response.status_code == 422 and response.json()["code"] == "unknown_product"


def test_decision_accepts_extra_fields_from_b(api):
    request = make_request("7701234567", "EXPRESS", 2_000_000, 12)
    request["company"] |= {"name": "ООО «Кофейня на Лесной»", "okved": "56.10", "tax_regime": "УСН"}
    request["enrichment"]["bki"]["requests_30d"] = 2
    assert api.post("/api/v1/decisions", json=request).status_code == 200
