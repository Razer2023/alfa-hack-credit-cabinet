"""Проверки защиты: чужие заявки, коды, статусы, сбои внешних сервисов."""

import uuid

from conftest import run_pipeline, submit

from app.clients import get_integrations
from app.clients.base import ExternalServiceError
from app.db import SessionLocal
from app.models import Application


def test_client_cannot_see_other_company(login):
    coffee, stroy = login("coffee"), login("stroy")
    app = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    assert stroy.get(f"/applications/{app['id']}").status_code == 404
    assert stroy.get("/applications").json() == []


def test_submit_requires_amount_term_purpose(login):
    coffee = login("coffee")
    app = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    response = coffee.post(f"/applications/{app['id']}/submit/code")
    assert response.status_code == 422
    assert "сумму, срок, цель" in response.json()["message"]


def test_unknown_product(login):
    response = login("coffee").post("/applications", {"product_code": "NOPE"})
    assert response.status_code == 422


def test_prefill_only_own_inn(login):
    coffee = login("coffee")
    app = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    response = coffee.post(f"/applications/{app['id']}/prefill", {"inn": "7702345678"})
    assert response.json()["code"] == "inn_mismatch"
    app = coffee.post(f"/applications/{app['id']}/prefill", {"inn": "7701234567"}).json()
    assert app["form"]["company"]["name"] == {"value": "ООО «Кофейня на Лесной»", "source": "EGRUL"}


def test_wrong_code_counts_attempts(login):
    coffee = login("coffee")
    app = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    path = f"/applications/{app['id']}"
    coffee.patch(path, {"amount": 1_000_000, "term_months": 6, "purpose": "Ремонт"})
    code = coffee.post(f"{path}/submit/code").json()
    wrong = "000000" if code["demo_code"] != "000000" else "111111"
    for left in (4, 3, 2, 1, 0):
        response = coffee.post(f"{path}/submit/confirm", {"confirmation_id": code["confirmation_id"], "code": wrong})
        assert response.json()["message"].endswith(str(left))
    response = coffee.post(f"{path}/submit/confirm", {"confirmation_id": code["confirmation_id"], "code": code["demo_code"]})
    assert response.json()["code"] == "too_many_attempts"


def test_code_is_single_use(login):
    coffee = login("coffee")
    app = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    path = f"/applications/{app['id']}"
    coffee.patch(path, {"amount": 1_000_000, "term_months": 6, "purpose": "Ремонт"})
    code = coffee.post(f"{path}/submit/code").json()
    body = {"confirmation_id": code["confirmation_id"], "code": code["demo_code"]}
    assert coffee.post(f"{path}/submit/confirm", body).status_code == 200
    assert coffee.post(f"{path}/submit/confirm", body).json()["code"] == "code_used"


def test_cannot_edit_after_submit(login):
    coffee = login("coffee")
    app = submit(coffee, "EXPRESS", 1_000_000, 6)
    response = coffee.patch(f"/applications/{app['id']}", {"amount": 5})
    assert response.status_code == 409


def test_cannot_sign_before_approval(login):
    coffee = login("coffee")
    app = submit(coffee, "EXPRESS", 1_000_000, 6)
    assert coffee.post(f"/applications/{app['id']}/sign/code").status_code == 409


def test_external_failure_is_retried(login, monkeypatch):
    coffee = login("coffee")
    app = submit(coffee, "EXPRESS", 1_000_000, 6)
    integrations = get_integrations()

    def broken(_):
        raise ExternalServiceError("integrations: timeout")

    monkeypatch.setattr(integrations, "check_application", broken)
    run_pipeline()
    with SessionLocal() as session:
        stored = session.get(Application, uuid.UUID(app["id"]))
        assert stored.status == "CHECKING"
        assert stored.retry_count == 1 and stored.retry_at is not None
    events = coffee.get(f"/applications/{app['id']}/events").json()
    assert events[-1]["type"] == "DELAYED"


def test_client_does_not_see_internal_events(login):
    vector, manager = login("vector"), login("manager")
    app = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    manager.post(f"/bank/applications/{app['id']}/take")
    client_types = {e["type"] for e in vector.get(f"/applications/{app['id']}/events").json()}
    bank_types = {e["type"] for e in manager.get(f"/bank/applications/{app['id']}/events").json()}
    assert "ASSIGNED" not in client_types and "ASSIGNED" in bank_types


def test_event_feed_after_id(login):
    coffee, stroy = login("coffee"), login("stroy")
    submit(coffee, "EXPRESS", 1_000_000, 6)
    last = coffee.get("/events").json()[-1]["id"]
    run_pipeline()
    fresh = coffee.get("/events", params={"after_id": last}).json()
    assert [e["to_status"] for e in fresh] == ["CHECKING", "SCORING", "APPROVED"]
    assert stroy.get("/events").json() == []


def test_catalog_and_payment(login):
    coffee = login("coffee")
    assert [p["code"] for p in coffee.get("/products").json()] == ["EXPRESS", "WORKING_CAPITAL", "INVESTMENT"]
    calc = coffee.post("/calc/payment", {"product_code": "EXPRESS", "amount": 1_200_000, "term_months": 12}).json()
    assert calc["total_payment"] == calc["monthly_payment"] * 12
    assert calc["overpayment"] > 0


def test_health(api):
    assert api.get("/health/ready").json() == {"status": "ok"}
