"""S4.10 — переписка клиента и банка внутри заявки, доставка через журнал событий."""

from conftest import run_pipeline, submit


def chat(login):
    coffee, manager = login("coffee"), login("manager")
    app = submit(coffee, "EXPRESS", 2_000_000, 12)
    run_pipeline()
    return coffee, manager, app["id"]


def test_client_and_manager_talk_in_application(login):
    coffee, manager, app_id = chat(login)

    sent = coffee.post(f"/applications/{app_id}/messages", {"text": "  Когда будет решение?  "})
    assert sent.status_code == 201
    assert sent.json()["author_role"] == "CLIENT" and sent.json()["text"] == "Когда будет решение?"

    reply = manager.post(f"/bank/applications/{app_id}/messages", {"text": "Сегодня до 18:00"}).json()
    assert reply["author_role"] == "MANAGER" and reply["author_name"] == "Смирнова Ольга Андреевна"

    for thread in (
        coffee.get(f"/applications/{app_id}/messages").json(),
        manager.get(f"/bank/applications/{app_id}/messages").json(),
    ):
        assert [m["text"] for m in thread] == ["Когда будет решение?", "Сегодня до 18:00"]
        assert thread[0]["author_name"] != "Смирнова Ольга Андреевна"


def test_messages_arrive_as_events(login):
    coffee, manager, app_id = chat(login)
    manager.post(f"/bank/applications/{app_id}/messages", {"text": "Добрый день! Заявку смотрю"})

    event = coffee.get(f"/applications/{app_id}/events").json()[-1]
    assert event["type"] == "MESSAGE"
    assert event["message"] == "Смирнова Ольга Андреевна: Добрый день! Заявку смотрю"

    coffee.post(f"/applications/{app_id}/messages", {"text": "Спасибо"})
    event = manager.get(f"/bank/applications/{app_id}/events").json()[-1]
    assert event["message"] == "ООО «Кофейня на Лесной»: Спасибо"


def test_chat_closed_for_drafts_and_strangers(login):
    coffee, stroy = login("coffee"), login("stroy")
    draft = coffee.post("/applications", {"product_code": "EXPRESS"}).json()
    response = coffee.post(f"/applications/{draft['id']}/messages", {"text": "Привет"})
    assert response.status_code == 409 and response.json()["code"] == "chat_unavailable"

    _, _, app_id = chat(login)
    assert stroy.get(f"/applications/{app_id}/messages").status_code == 404
    assert coffee.get(f"/bank/applications/{app_id}/messages").status_code == 403


def test_empty_and_long_messages_rejected(login):
    coffee, _, app_id = chat(login)
    assert coffee.post(f"/applications/{app_id}/messages", {"text": "   "}).status_code == 422
    assert coffee.post(f"/applications/{app_id}/messages", {"text": "x" * 2001}).status_code == 422
