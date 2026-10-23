from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _request() -> dict:
    response = client.post(
        "/api/v1/document-requests",
        json={
            "application_id": "11111111-1111-1111-1111-111111111111",
            "inn": "7701234567",
            "comment": "Нужны документы по запросу банка",
            "items": [
                {"code": "charter", "title": "Устав"},
                {"code": "statement", "title": "Выписка по счёту"},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_request_starts_open():
    body = _request()
    assert body["status"] == "OPEN"
    assert [item["status"] for item in body["items"]] == ["WAITING", "WAITING"]


def test_upload_completes_request_and_returns_file():
    created = _request()
    request_id = created["id"]
    first = client.post(
        f"/api/v1/document-requests/{request_id}/items/charter",
        content=PDF,
        headers={"content-type": "application/pdf", "x-filename": "ustav.pdf"},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "OPEN"
    charter = next(item for item in first.json()["items"] if item["code"] == "charter")
    assert charter["status"] == "RECEIVED"
    assert charter["filename"] == "ustav.pdf"
    assert charter["size"] == len(PDF)

    second = client.post(
        f"/api/v1/document-requests/{request_id}/items/statement",
        content=PDF,
        headers={"content-type": "application/pdf", "x-filename": "statement.pdf"},
    )
    assert second.json()["status"] == "COMPLETE"

    downloaded = client.get(f"/api/v1/document-requests/{request_id}/items/charter/file")
    assert downloaded.status_code == 200
    assert downloaded.content == PDF
    assert downloaded.headers["content-type"].startswith("application/pdf")


def test_rejects_unknown_type_and_missing_request():
    created = _request()
    rejected = client.post(
        f"/api/v1/document-requests/{created['id']}/items/charter",
        content=b"hello",
        headers={"content-type": "text/plain", "x-filename": "note.txt"},
    )
    assert rejected.status_code == 400
    assert client.get("/api/v1/document-requests/missing").status_code == 404


def test_lists_requests_of_one_application():
    created = _request()
    listed = client.get("/api/v1/document-requests", params={"application_id": created["application_id"]}).json()
    assert any(row["id"] == created["id"] for row in listed)
