"""S4.9 — клиент видит, кто ведёт заявку и как связаться; S4.6 — срок решения по этапам."""

from datetime import datetime, timedelta

from conftest import run_pipeline, submit


def test_manager_assigned_on_submit_and_visible_to_client(login):
    coffee = login("coffee")
    app = submit(coffee, "EXPRESS", 2_000_000, 12)
    assert app["manager"] is None  # назначается конвейером при отправке

    run_pipeline()
    app = coffee.get(f"/applications/{app['id']}").json()
    assert app["manager"] == {
        "full_name": "Смирнова Ольга Андреевна",
        "position": "Кредитный менеджер малого бизнеса",
        "phone": "+7 495 000-00-01",
        "work_hours": "пн–пт 9:00–19:00",
    }
    events = coffee.get(f"/applications/{app['id']}/events").json()
    assert any(e["type"] == "MANAGER_ASSIGNED" and "Смирнова Ольга" in e["message"] for e in events)


def test_draft_has_no_manager(login):
    coffee = login("coffee")
    app = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    assert app["manager"] is None


def test_manager_who_takes_application_becomes_contact(login):
    vector, manager = login("vector"), login("manager")
    app = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    manager.post(f"/bank/applications/{app['id']}/take")
    assert vector.get(f"/applications/{app['id']}").json()["manager"]["phone"] == "+7 495 000-00-01"


def test_status_has_sla_and_due_time(login):
    coffee = login("coffee")
    app = submit(coffee, "EXPRESS", 2_000_000, 12)
    run_pipeline()
    status = coffee.get(f"/applications/{app['id']}").json()["status"]
    assert status["code"] == "PENDING_APPROVAL"
    assert status["sla"] == "до 2 часов в рабочее время"

    changed = datetime.fromisoformat(coffee.get(f"/applications/{app['id']}").json()["status_changed_at"])
    due = datetime.fromisoformat(status["due_at"])
    assert due.replace(tzinfo=None) - changed.replace(tzinfo=None) == timedelta(hours=2)


def test_client_turn_has_no_sla(login):
    coffee = login("coffee")
    draft = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    assert draft["status"]["sla"] is None and draft["status"]["due_at"] is None


def test_status_reference_lists_sla(login):
    statuses = {s["code"]: s for s in login("coffee").get("/reference/statuses").json()}
    assert statuses["MANUAL_REVIEW"]["sla"] == "до 1 рабочего дня"
    assert statuses["APPROVED"]["sla"] is None
