"""Описание JSON-полей заявки в контракте: схемы есть, а данные проходят через ядро без изменений."""

from conftest import run_pipeline, submit

from app.clients import get_scoring
from app.main import app

# Ответ в формате настоящего сервиса C (services/scoring): с metrics, factors[].value и полем, которого ядро не знает
SCORING_RESPONSE = {
    "result": "MANUAL_REVIEW",
    "score": 455,
    "risk_class": "C",
    "model_version": "scorecard-1.0+products-1.0",
    "factors": [
        {"code": "BUSINESS_AGE", "title": "Возраст бизнеса", "impact": 60, "value": "5,1 года"},
        {"code": "BKI_OVERDUE", "title": "Просрочки в БКИ", "impact": -80, "value": "45 дн."},
    ],
    "reasons": [{"code": "BKI_OVERDUE", "text": "Просрочка 45 дн. в БКИ"}],
    "offers": [],
    "metrics": {
        "limit": 4_500_000,
        "monthly_free_cash_flow": 300_000,
        "existing_debt_payment": 190_000,
        "new_payment": 280_000,
        "dscr": 1.1,
        "min_dscr": 1.25,
    },
    "explain_url": "/rules/scorecard-1.0",
}


def test_json_fields_are_described_in_contract():
    schemas = app.openapi()["components"]["schemas"]
    bank = schemas["ApplicationBankOut"]["properties"]
    for field, schema in {
        "form": "ApplicationForm",
        "need_info": "NeedInfo",
        "decision": "Decision",
        "enrichment": "Enrichment",
        "scoring": "ScoringResult",
    }.items():
        assert schema in str(bank[field]), field
    assert schemas["DataSource"]["enum"] == ["EGRUL", "FNS", "BANK_ACCOUNT"]
    assert schemas["Decision"]["properties"]["decided_by"]["enum"] == ["SYSTEM", "UNDERWRITER"]
    assert set(schemas["Decision"]["properties"]["result"]["enum"]) == {"APPROVE", "COUNTER_OFFER", "REJECT", "MANUAL_REVIEW"}


def test_scoring_response_passes_through_unchanged(login, monkeypatch):
    monkeypatch.setattr(get_scoring(), "decide", lambda request: SCORING_RESPONSE)
    vector, underwriter = login("vector"), login("underwriter")
    app_ = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()

    card = underwriter.get(f"/bank/applications/{app_['id']}").json()
    assert card["scoring"] == SCORING_RESPONSE
    assert card["enrichment"]["bki"] == {"max_overdue_days": 45, "active_loans": 3, "total_debt": 6_000_000}
    assert card["decision"] == {
        "result": "MANUAL_REVIEW",
        "decided_by": "SYSTEM",
        "reasons": [{"code": "BKI_OVERDUE", "text": "Просрочка 45 дн. в БКИ"}],
        "comment": None,
    }
    assert card["form"]["company"]["employees"] == {"value": 9, "source": "FNS"}


def test_need_info_shape(login):
    vector, manager = login("vector"), login("manager")
    app_ = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    request = {"items": [{"field": "overdue_explanation", "message": "Поясните просрочку"}], "comment": "Срочно"}
    manager.post(f"/bank/applications/{app_['id']}/info-request", request)

    need_info = vector.get(f"/applications/{app_['id']}").json()["need_info"]
    assert need_info == {**request, "requested_by": "MANAGER"}
