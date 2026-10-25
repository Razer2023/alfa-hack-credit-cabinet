"""S4.4 — банк запрашивает документы и объясняет, зачем каждый; S4.7 — клиент загружает их в кабинете."""

from urllib.parse import quote

from conftest import run_pipeline, submit

PDF = b"%PDF-1.4 synthetic test document"
ASK = {
    "items": [
        {"title": "Договор с заказчиком", "reason": "Подтвердить выручку, на которую рассчитан кредит"},
        {"title": "Справка об отсутствии долгов", "reason": "Проверить, что просрочка закрыта"},
    ],
    "comment": "Можно фото или скан",
}


def requested(login):
    vector, underwriter = login("vector"), login("underwriter")
    app = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    card = underwriter.post(f"/bank/applications/{app['id']}/document-request", ASK).json()
    return vector, underwriter, app["id"], card


def upload(client, app_id, item, payload=PDF, content_type="application/pdf", filename="договор.pdf"):
    doc = item["document"]
    return client.api.post(
        f"/api/v1/applications/{app_id}/documents/{doc['request_id']}/{doc['code']}",
        content=payload,
        headers=client.headers | {"Content-Type": content_type, "X-Filename": quote(filename)},
    )


def test_bank_requests_documents_with_reasons(login):
    vector, _, app_id, card = requested(login)
    assert card["status"]["code"] == "NEED_INFO"

    app = vector.get(f"/applications/{app_id}").json()
    items = app["need_info"]["items"]
    assert [i["message"] for i in items] == ["Договор с заказчиком", "Справка об отсутствии долгов"]
    assert items[0]["reason"] == "Подтвердить выручку, на которую рассчитан кредит"
    assert items[0]["document"]["code"] == "doc1"
    assert app["need_info"]["comment"] == "Можно фото или скан"

    docs = vector.get(f"/applications/{app_id}/documents").json()
    assert [i["status"] for i in docs[0]["items"]] == ["WAITING", "WAITING"]
    assert docs[0]["items"][1]["reason"] == "Проверить, что просрочка закрыта"

    events = vector.get(f"/applications/{app_id}/events").json()
    assert "Договор с заказчиком" in events[-1]["message"]


def test_cannot_continue_until_all_documents_uploaded(login):
    vector, _, app_id, _ = requested(login)
    items = vector.get(f"/applications/{app_id}").json()["need_info"]["items"]

    assert upload(vector, app_id, items[0]).status_code == 200
    response = vector.post(f"/applications/{app_id}/info", {"comment": "Готово"})
    assert response.status_code == 422
    assert response.json()["message"] == "Загрузите документы: Справка об отсутствии долгов"

    upload(vector, app_id, items[1], payload=b"\x89PNG fake", content_type="image/png", filename="справка.png")
    assert vector.post(f"/applications/{app_id}/info", {"comment": "Готово"}).json()["status"]["code"] == "CHECKING"


def test_bank_downloads_uploaded_file(login):
    vector, underwriter, app_id, _ = requested(login)
    item = vector.get(f"/applications/{app_id}").json()["need_info"]["items"][0]
    upload(vector, app_id, item)

    doc = item["document"]
    response = underwriter.get(f"/bank/applications/{app_id}/documents/{doc['request_id']}/{doc['code']}")
    assert response.status_code == 200
    assert response.content == PDF
    assert response.headers["content-type"] == "application/pdf"
    # Исходное имя с кириллицей — из журнала заявки, хотя сервис B хранит имя латиницей
    assert response.headers["content-disposition"] == "attachment; filename*=UTF-8''%D0%B4%D0%BE%D0%B3%D0%BE%D0%B2%D0%BE%D1%80.pdf"

    docs = underwriter.get(f"/bank/applications/{app_id}/documents").json()
    assert docs[0]["items"][0]["status"] == "RECEIVED"
    assert docs[0]["items"][0]["filename"] == "договор.pdf"
    bank_events = underwriter.get(f"/bank/applications/{app_id}/events").json()
    assert any(e["type"] == "DOCUMENT_UPLOADED" for e in bank_events)


def test_upload_rules(login):
    vector, _, app_id, _ = requested(login)
    item = vector.get(f"/applications/{app_id}").json()["need_info"]["items"][0]

    wrong_type = upload(vector, app_id, item, content_type="text/plain")
    assert wrong_type.status_code == 422 and wrong_type.json()["message"] == "Нужен файл PDF, JPEG или PNG"

    fake = item | {"document": {"request_id": item["document"]["request_id"], "code": "doc99"}}
    assert upload(vector, app_id, fake).json()["code"] == "document_not_requested"

    stroy = login("stroy")
    assert upload(stroy, app_id, item).status_code == 404  # чужая заявка


def test_document_request_needs_bank_role_and_status(login):
    coffee, manager = login("coffee"), login("manager")
    draft = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    response = manager.post(f"/bank/applications/{draft['id']}/document-request", ASK)
    assert response.status_code == 409
    assert coffee.post(f"/bank/applications/{draft['id']}/document-request", ASK).status_code == 403


def test_reasons_stay_after_request_is_answered(login):
    vector, underwriter, app_id, _ = requested(login)
    for item in vector.get(f"/applications/{app_id}").json()["need_info"]["items"]:
        upload(vector, app_id, item)
    vector.post(f"/applications/{app_id}/info", {})
    docs = underwriter.get(f"/bank/applications/{app_id}/documents").json()
    assert docs[0]["items"][0]["reason"] == "Подтвердить выручку, на которую рассчитан кредит"


def test_questions_and_documents_in_one_request(login):
    vector, underwriter = login("vector"), login("underwriter")
    app = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    body = {
        "items": [{"field": "overdue", "message": "Поясните просрочку в БКИ"}],
        "documents": [{"title": "Справка об отсутствии долгов", "reason": "Проверить, что просрочка закрыта"}],
        "comment": "Можно фото",
    }
    card = underwriter.post(f"/bank/applications/{app['id']}/info-request", body).json()
    assert card["status"]["code"] == "NEED_INFO"

    items = vector.get(f"/applications/{app['id']}").json()["need_info"]["items"]
    assert [i["message"] for i in items] == ["Поясните просрочку в БКИ", "Справка об отсутствии долгов"]
    assert items[0]["document"] is None and items[1]["document"]["code"] == "doc1"
    event = vector.get(f"/applications/{app['id']}/events").json()[-1]
    assert event["message"] == "Банк попросил дополнить заявку и запросил документы: Справка об отсутствии долгов"


def test_empty_request_rejected(login):
    vector, underwriter = login("vector"), login("underwriter")
    app = submit(vector, "WORKING_CAPITAL", 3_000_000, 12)
    run_pipeline()
    assert underwriter.post(f"/bank/applications/{app['id']}/info-request", {"items": []}).status_code == 422
