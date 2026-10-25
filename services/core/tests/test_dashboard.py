"""S8.1 — дашборд узких мест: время в каждом статусе по журналу событий и по демо-массиву B."""

from datetime import timedelta

from conftest import confirm, run_pipeline, submit

from app import dashboard
from app.db import SessionLocal, utcnow


def stages(result):
    return {stage["code"]: stage for stage in result["stages"]}


def test_live_counts_time_in_each_status(login):
    coffee, manager = login("coffee"), login("manager")
    first = submit(coffee, "EXPRESS", 2_000_000, 12)
    submit(coffee, "EXPRESS", 1_000_000, 12)
    run_pipeline()
    confirm(manager, first["id"])

    result = manager.get("/bank/dashboard").json()
    assert result["source"] == "LIVE" and result["applications"] == 2
    by_code = stages(result)
    assert by_code["CHECKING"]["passed"] == 2 and by_code["SCORING"]["owner"] == "SYSTEM"
    assert by_code["PENDING_APPROVAL"]["passed"] == 1 and by_code["PENDING_APPROVAL"]["in_progress"] == 1
    assert by_code["APPROVED"]["owner"] == "CLIENT" and by_code["APPROVED"]["in_progress"] == 1
    assert {s["code"]: s["count"] for s in result["by_status"]} == {"PENDING_APPROVAL": 1, "APPROVED": 1}


def test_waiting_over_sla_becomes_bottleneck(login):
    coffee = login("coffee")
    submit(coffee, "EXPRESS", 2_000_000, 12)
    run_pipeline()
    with SessionLocal() as session:
        result = dashboard.live(session, now=utcnow() + timedelta(hours=3))

    waiting = stages(result)["PENDING_APPROVAL"]
    assert waiting["in_progress"] == 1 and waiting["over_sla"] == 1 and waiting["longest_wait_minutes"] >= 180
    assert result["bottleneck"] == "PENDING_APPROVAL"
    assert "«Ждёт подтверждения»" in result["bottleneck_text"] and "Срок нарушен у 1" in result["bottleneck_text"]


def test_demo_from_integrations(login):
    result = login("underwriter").get("/bank/dashboard", params={"source": "DEMO"}).json()
    assert result["source"] == "DEMO" and result["applications"] == 4
    by_code = stages(result)
    assert by_code["CHECKING"]["passed"] == 4 and by_code["CHECKING"]["over_sla"] == 4
    assert by_code["MANUAL_REVIEW"]["passed"] == 2  # 0 минут — этап не проходили
    assert by_code["APPROVED"]["owner"] == "CLIENT"
    assert result["bottleneck"] == "MANUAL_REVIEW"


def test_only_for_bank(login):
    assert login("coffee").get("/bank/dashboard").status_code == 403
    assert login("manager").get("/bank/dashboard", params={"source": "NOPE"}).status_code == 422
