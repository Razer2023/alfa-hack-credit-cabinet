from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DEMOS = {
    "7701234567": "APPROVED",
    "7702345678": "COUNTER_OFFER",
    "7703456789": "MANUAL_REVIEW",
}


def test_dashboard_has_demo_companies_and_volume():
    rows = client.get("/api/v1/dashboard/applications").json()
    assert len(rows) >= 30
    by_inn = {row["inn"]: row for row in rows}
    for inn, result in DEMOS.items():
        assert by_inn[inn]["result"] == result
        assert set(by_inn[inn]["stage_minutes"]) == {"checking", "scoring", "manual_review", "signing"}
    assert by_inn["7703456789"]["stage_minutes"]["manual_review"] > 0
    assert by_inn["7701234567"]["stage_minutes"]["manual_review"] == 0
