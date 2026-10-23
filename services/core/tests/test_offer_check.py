"""S5.4: условия сотрудника банка проверяются скорингом перед подтверждением."""

import pytest
from conftest import confirm, run_pipeline, submit

from app.clients import get_scoring
from app.clients.base import ExternalServiceError

# Ответ сервиса C, когда условия не проходят политику (пример из ТЗ tz/A-core/2026-10-23-c-offer-check.md)
NOT_ALLOWED = {
    "allowed": False,
    "terms": {"amount": 10_000_000, "term_months": 12, "rate": 18.9},
    "monthly_payment": 921_089,
    "checks": [
        {"code": "DSCR_TOO_LOW", "level": "error", "text": "Компания не потянет платёж: DSCR 0,46 при минимуме 1,25"}
    ],
    "suggestion": {"amount": 2_600_000, "term_months": 12, "rate": 18.9},
    "score": 740,
    "risk_class": "A",
    "model_version": "scorecard-1.1+products-1.0",
    "metrics": {"limit": 10_500_000, "dscr": 0.46, "min_dscr": 1.25},
}
TERMS = {"result": "APPROVE", "amount": 10_000_000, "term_months": 12}


@pytest.fixture
def strict_scoring(monkeypatch):
    """Скоринг пропускает только условия до 2,6 млн, остальное — с ошибкой DSCR."""
    scoring = get_scoring()
    calls = []
    original = scoring.check_offer

    def check(request):
        calls.append(request)
        return NOT_ALLOWED if request["terms"]["amount"] > 2_600_000 else original(request)

    monkeypatch.setattr(scoring, "check_offer", check)
    return calls


def pending(login):
    stroy = login("stroy")
    app = submit(stroy, "WORKING_CAPITAL", 10_000_000, 12)
    run_pipeline()
    return app["id"]


def test_manager_cannot_confirm_terms_outside_policy(login, strict_scoring):
    app_id = pending(login)
    manager = login("manager")

    response = manager.post(f"/bank/applications/{app_id}/decision", TERMS)
    assert response.status_code == 422
    error = response.json()
    assert error["code"] == "offer_not_allowed"
    assert "DSCR 0,46" in error["message"] and "2 600 000" in error["message"]

    # Запрос в скоринг — снимок заявки с данными проверок и условиями сотрудника
    request = strict_scoring[-1]
    assert request["terms"] == {"amount": 10_000_000, "term_months": 12, "rate": 19.9}
    assert request["enrichment"]["bki"] and request["application"]["product_code"] == "WORKING_CAPITAL"

    card = manager.get(f"/bank/applications/{app_id}").json()
    assert card["status"]["code"] == "PENDING_APPROVAL" and card["offers"] == []


def test_underwriter_overrides_only_with_comment(login, strict_scoring):
    app_id = pending(login)
    underwriter = login("underwriter")

    response = underwriter.post(f"/bank/applications/{app_id}/decision", TERMS)
    assert response.json()["code"] == "override_comment_required"

    body = TERMS | {"comment": "Госконтракт на 40 млн, оплата через 3 месяца"}
    card = underwriter.post(f"/bank/applications/{app_id}/decision", body).json()
    assert card["status"]["code"] == "APPROVED"
    assert card["decision"]["override"] is True
    assert card["decision"]["checks"][0]["code"] == "DSCR_TOO_LOW"

    bank_events = underwriter.get(f"/bank/applications/{app_id}/events").json()
    assert bank_events[-1]["type"] == "POLICY_OVERRIDE" and "Госконтракт" in bank_events[-1]["message"]
    client_events = login("stroy").get(f"/applications/{app_id}/events").json()
    assert "POLICY_OVERRIDE" not in {event["type"] for event in client_events}


def test_terms_within_policy_pass_as_before(login, strict_scoring):
    app_id = pending(login)
    body = {"result": "COUNTER_OFFER", "amount": 2_500_000, "term_months": 12}
    card = login("manager").post(f"/bank/applications/{app_id}/decision", body).json()
    assert card["status"]["code"] == "COUNTER_OFFER"
    assert card["decision"]["override"] is False


def test_recommendation_is_confirmed_as_before(login):
    app_id = pending(login)
    card = confirm(login("manager"), app_id, "COUNTER_OFFER")
    assert card["status"]["code"] == "COUNTER_OFFER"
    assert card["decision"]["checks"] == [] and card["decision"]["override"] is False


def test_scoring_unavailable_does_not_block(login, monkeypatch):
    app_id = pending(login)

    def broken(_):
        raise ExternalServiceError("scoring: timeout")

    monkeypatch.setattr(get_scoring(), "check_offer", broken)
    card = confirm(login("manager"), app_id, "COUNTER_OFFER")
    assert card["status"]["code"] == "COUNTER_OFFER"
    assert card["decision"]["checks"][0] == {
        "code": "CHECK_UNAVAILABLE",
        "level": "warning",
        "text": "Скоринг недоступен — условия не проверены по политике банка",
    }


def test_offer_check_endpoint_for_form(login, strict_scoring):
    app_id = pending(login)
    manager = login("manager")

    check = manager.post(f"/bank/applications/{app_id}/offer-check", {"amount": 10_000_000, "term_months": 12}).json()
    assert check["allowed"] is False
    assert check["suggestion"]["amount"] == 2_600_000
    assert check["metrics"]["dscr"] == 0.46
    assert strict_scoring[-1]["terms"]["rate"] is None  # ставку подставит скоринг по классу риска

    ok = manager.post(f"/bank/applications/{app_id}/offer-check", {"amount": 2_000_000, "term_months": 12}).json()
    assert ok["allowed"] is True

    # Проверка ничего не меняет в заявке
    assert manager.get(f"/bank/applications/{app_id}").json()["status"]["code"] == "PENDING_APPROVAL"
    assert login("stroy").post(f"/bank/applications/{app_id}/offer-check", {"amount": 1, "term_months": 1}).status_code == 403
