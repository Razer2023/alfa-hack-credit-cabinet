"""Сквозные сценарии трёх демо-компаний: одобрение, контрпредложение, ручное рассмотрение."""

from conftest import confirm, run_pipeline, sign, submit


def statuses(client, app_id: str) -> list[str]:
    return [e["to_status"] for e in client.get(f"/applications/{app_id}/events").json() if e["to_status"]]


def test_approve_sign_issue(login):
    coffee, manager = login("coffee"), login("manager")
    app = submit(coffee, "EXPRESS", 2_000_000, 12)
    assert app["status"]["code"] == "SUBMITTED"

    run_pipeline()
    app = coffee.get(f"/applications/{app['id']}").json()
    assert app["status"]["code"] == "PENDING_APPROVAL"
    assert app["offers"] == [] and app["allowed_actions"] == []

    card = confirm(manager, app["id"])
    assert card["decision"]["decided_by"] == "MANAGER"
    app = coffee.get(f"/applications/{app['id']}").json()
    assert app["status"]["code"] == "APPROVED"
    assert app["allowed_actions"] == ["SIGN", "CANCEL"]
    [offer] = app["offers"]
    assert (offer["amount"], offer["term_months"], offer["kind"]) == (2_000_000, 12, "STANDARD")
    assert offer["monthly_payment"] > 2_000_000 / 12

    assert sign(coffee, app["id"])["status"]["code"] == "SIGNED"
    run_pipeline()
    app = coffee.get(f"/applications/{app['id']}").json()
    assert app["status"]["code"] == "ISSUED"
    assert app["offers"][0]["status"] == "ACCEPTED"
    assert statuses(coffee, app["id"]) == [
        "DRAFT", "SUBMITTED", "CHECKING", "SCORING", "PENDING_APPROVAL", "APPROVED", "SIGNED", "ISSUED",
    ]


def test_counter_offer_accepted(login):
    stroy, manager = login("stroy"), login("manager")
    app = submit(stroy, "WORKING_CAPITAL", 10_000_000, 12)
    run_pipeline()
    confirm(manager, app["id"], "COUNTER_OFFER")
    app = stroy.get(f"/applications/{app['id']}").json()
    assert app["status"]["code"] == "COUNTER_OFFER"
    assert app["decision"]["reasons"][0]["code"] == "AMOUNT_OVER_LIMIT"  # объяснение скоринга видно клиенту
    [offer] = app["offers"]
    assert offer["kind"] == "COUNTER" and offer["amount"] < 10_000_000

    response = stroy.post(f"/applications/{app['id']}/offers/{offer['id']}/accept")
    assert response.json()["status"]["code"] == "APPROVED"
    sign(stroy, app["id"])
    run_pipeline()
    assert stroy.get(f"/applications/{app['id']}").json()["status"]["code"] == "ISSUED"


def test_counter_offer_declined(login):
    stroy, manager = login("stroy"), login("manager")
    app = submit(stroy, "WORKING_CAPITAL", 10_000_000, 12)
    run_pipeline()
    confirm(manager, app["id"], "COUNTER_OFFER")
    app = stroy.post(f"/applications/{app['id']}/cancel", {"reason": "Нужна вся сумма"}).json()
    assert app["status"]["code"] == "CANCELLED"
    assert app["offers"][0]["status"] == "DECLINED"


def test_manual_review_with_info_request_then_reject(login):
    vector, underwriter = login("vector"), login("underwriter")
    app = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    assert vector.get(f"/applications/{app['id']}").json()["status"]["code"] == "MANUAL_REVIEW"

    queue = underwriter.get("/bank/applications", params={"status": "MANUAL_REVIEW"}).json()
    assert [a["id"] for a in queue] == [app["id"]]
    card = underwriter.post(f"/bank/applications/{app['id']}/take").json()
    assert card["enrichment"]["bki"]["max_overdue_days"] == 45
    assert card["scoring"]["result"] == "MANUAL_REVIEW"

    request = {"items": [{"field": "overdue_explanation", "message": "Поясните просрочку 2025 года"}]}
    underwriter.post(f"/bank/applications/{app['id']}/info-request", request)
    app = vector.get(f"/applications/{app['id']}").json()
    assert app["status"]["code"] == "NEED_INFO"
    assert app["need_info"]["items"][0]["field"] == "overdue_explanation"

    vector.post(f"/applications/{app['id']}/info", {"extra": {"overdue_explanation": "Задержка оплаты от заказчика"}})
    run_pipeline()
    assert vector.get(f"/applications/{app['id']}").json()["status"]["code"] == "MANUAL_REVIEW"

    card = underwriter.post(f"/bank/applications/{app['id']}/decision", {"result": "REJECT", "comment": "Высокий риск"}).json()
    assert card["status"]["code"] == "REJECTED"
    app = vector.get(f"/applications/{app['id']}").json()
    assert app["decision"]["reasons"][0]["text"] == "Высокий риск"


def test_underwriter_counter_offer(login):
    vector, underwriter = login("vector"), login("underwriter")
    app = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    decision = {"result": "COUNTER_OFFER", "amount": 1_500_000, "term_months": 18}
    card = underwriter.post(f"/bank/applications/{app['id']}/decision", decision).json()
    assert card["status"]["code"] == "COUNTER_OFFER"
    assert card["offers"][0]["created_at"]
    assert (card["offers"][0]["amount"], card["offers"][0]["kind"]) == (1_500_000, "COUNTER")


def test_manager_cannot_decide(login):
    vector, manager = login("vector"), login("manager")
    app = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    response = manager.post(f"/bank/applications/{app['id']}/decision", {"result": "APPROVE"})
    assert response.status_code == 403


def test_system_asks_for_missing_company_data(login):
    coffee = login("coffee")
    app = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    path = f"/applications/{app['id']}"
    coffee.patch(path, {"amount": 1_000_000, "term_months": 6, "purpose": "Ремонт"})
    code = coffee.post(f"{path}/submit/code").json()
    coffee.post(f"{path}/submit/confirm", {"confirmation_id": code["confirmation_id"], "code": code["demo_code"]})
    run_pipeline()

    app = coffee.get(path).json()
    assert app["status"]["code"] == "NEED_INFO"
    assert app["allowed_actions"] == ["PROVIDE_INFO", "CANCEL"]
    assert app["need_info"]["items"][0]["field"] == "company"

    coffee.post(f"{path}/prefill", {"inn": "7701234567"})
    coffee.post(f"{path}/info", {"comment": "Заполнил"})
    run_pipeline()
    assert coffee.get(path).json()["status"]["code"] == "PENDING_APPROVAL"


def test_no_automatic_approval():
    from app.models import ApplicationStatus as S
    from app.models import Role
    from app.statemachine import TRANSITIONS

    automatic = {dst for (src, dst), roles in TRANSITIONS.items() if Role.SYSTEM in roles}
    assert S.APPROVED not in automatic and S.COUNTER_OFFER not in automatic


def test_manager_confirms_but_cannot_reject(login):
    coffee, manager, underwriter = login("coffee"), login("manager"), login("underwriter")
    app = submit(coffee, "EXPRESS", 2_000_000, 12)
    run_pipeline()

    queue = manager.get("/bank/applications", params={"status": "PENDING_APPROVAL"}).json()
    assert [a["id"] for a in queue] == [app["id"]]
    assert queue[0]["scoring"]["result"] == "APPROVE"
    assert "ESCALATE" in queue[0]["allowed_actions"]

    response = manager.post(f"/bank/applications/{app['id']}/decision", {"result": "REJECT", "comment": "Нет"})
    assert response.status_code == 403

    card = confirm(underwriter, app["id"])
    assert card["status"]["code"] == "APPROVED"
    assert card["decision"]["decided_by"] == "UNDERWRITER"


def test_manager_escalates_to_underwriter(login):
    coffee, manager, underwriter = login("coffee"), login("manager"), login("underwriter")
    app = submit(coffee, "EXPRESS", 2_000_000, 12)
    run_pipeline()

    card = manager.post(f"/bank/applications/{app['id']}/escalate", {"comment": "Сомневаюсь в выручке"}).json()
    assert card["status"]["code"] == "MANUAL_REVIEW"
    assert underwriter.post(f"/bank/applications/{app['id']}/escalate", {}).status_code == 403
    assert manager.post(f"/bank/applications/{app['id']}/decision", {"result": "APPROVE"}).status_code == 403
    assert confirm(underwriter, app["id"])["status"]["code"] == "APPROVED"


def test_staff_can_change_recommended_terms(login):
    coffee, manager = login("coffee"), login("manager")
    app = submit(coffee, "EXPRESS", 2_000_000, 12)
    run_pipeline()
    decision = {"result": "COUNTER_OFFER", "amount": 1_500_000, "term_months": 18}
    card = manager.post(f"/bank/applications/{app['id']}/decision", decision).json()
    assert card["status"]["code"] == "COUNTER_OFFER"
    assert (card["offers"][0]["amount"], card["offers"][0]["term_months"]) == (1_500_000, 18)
