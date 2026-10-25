"""S2.1 — предоценка суммы и шансов по ИНН до подачи заявки, без сохранения."""

from app.db import SessionLocal
from app.models import Application, ApplicationEvent


def precheck(client, body):
    return client.post("/precheck", body)


def test_high_chance_and_max_amount(login):
    result = precheck(login("coffee"), {"product_code": "EXPRESS", "amount": 2_000_000, "term_months": 12}).json()
    assert result["chance"] == "HIGH"
    assert result["title"] == "Шансы высокие"
    assert result["max_amount"] == 5_000_000  # граница продукта: лимит компании выше
    assert result["terms"]["amount"] == 2_000_000 and result["terms"]["monthly_payment"] > 0
    assert "одобрим эту сумму" in result["explanation"]


def test_counter_offer_shows_reachable_amount(login):
    result = precheck(login("stroy"), {"product_code": "WORKING_CAPITAL", "amount": 10_000_000, "term_months": 12}).json()
    assert result["chance"] == "MEDIUM"
    assert result["max_amount"] == 7_500_000
    assert result["terms"]["amount"] == 7_500_000
    assert result["reasons"] == ["Запрошенная сумма выше допустимой по выручке"]
    assert "можем предложить 7 500 000 ₽" in result["explanation"]


def test_manual_review_has_no_amount(login):
    result = precheck(login("vector"), {"product_code": "WORKING_CAPITAL", "amount": 3_000_000, "term_months": 12}).json()
    assert result["chance"] == "MEDIUM"
    assert result["max_amount"] is None and result["terms"] is None
    assert result["reasons"] == ["Просрочка 45 дн. в БКИ"]


def test_without_amount_estimates_maximum_only(login):
    result = precheck(login("stroy"), {"product_code": "WORKING_CAPITAL"}).json()
    assert result["max_amount"] == 7_500_000
    assert result["terms"]["amount"] == 7_500_000


def test_nothing_is_saved(login):
    precheck(login("coffee"), {"product_code": "EXPRESS", "amount": 2_000_000, "term_months": 12})
    with SessionLocal() as session:
        assert session.query(Application).count() == 0
        assert session.query(ApplicationEvent).count() == 0


def test_only_clients_and_known_products(login):
    assert precheck(login("manager"), {"product_code": "EXPRESS"}).status_code == 403
    assert precheck(login("coffee"), {"product_code": "NOPE"}).status_code == 422
