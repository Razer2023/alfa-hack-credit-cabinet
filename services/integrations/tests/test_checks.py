from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def application(**overrides) -> dict:
    body = {
        "application_id": "11111111-1111-1111-1111-111111111111",
        "inn": "7701234567",
        "application": {
            "product_code": "EXPRESS",
            "amount": 2_000_000,
            "term_months": 12,
            "purpose": "Закупка товара",
        },
        "company": {"name": "ООО «Кофейня на Лесной»", "revenue_year": 24_000_000},
        "extra": {},
    }
    body.update(overrides)
    return body


def test_full_application_is_complete():
    body = client.post("/api/v1/checks", json=application()).json()
    assert body["complete"] is True
    assert body["missing"] == []
    assert body["enrichment"]["bki"] == {
        "max_overdue_days": 0,
        "active_loans": 1,
        "total_debt": 400_000,
    }


def test_missing_purpose_matches_core_stub():
    payload = application()
    payload["application"]["purpose"] = "  "
    body = client.post("/api/v1/checks", json=payload).json()
    assert body["complete"] is False
    assert {"field": "purpose", "message": "Укажите цель кредита"} in body["missing"]


def test_zero_amount_asks_to_fill_it():
    payload = application()
    payload["application"]["amount"] = 0
    body = client.post("/api/v1/checks", json=payload).json()
    assert {"field": "amount", "message": "Укажите сумму кредита"} in body["missing"]


def test_negative_amount_is_incorrect():
    payload = application()
    payload["application"]["amount"] = -100
    body = client.post("/api/v1/checks", json=payload).json()
    assert body["missing"] == [
        {"field": "amount", "message": "Сумма кредита должна быть целым числом больше нуля"}
    ]


def test_bad_term_is_incorrect():
    payload = application()
    payload["application"]["term_months"] = "год"
    body = client.post("/api/v1/checks", json=payload).json()
    assert {"field": "term_months", "message": "Срок кредита должен быть целым числом месяцев больше нуля"} in body["missing"]


def test_empty_company_matches_core_stub():
    body = client.post("/api/v1/checks", json=application(company={})).json()
    assert {"field": "company", "message": "Заполните данные компании по ИНН"} in body["missing"]


def test_inn_must_be_digits():
    body = client.post("/api/v1/checks", json=application(inn="77-01")).json()
    assert {"field": "inn", "message": "ИНН должен содержать 10 или 12 цифр"} in body["missing"]
