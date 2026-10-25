"""S1.2 — подбор продукта по цели, сумме и сроку по прозрачным правилам каталога."""


def match(client, body):
    response = client.post("/products/match", body)
    assert response.status_code == 200, response.text
    return response.json()


def test_purposes_without_duplicates(login):
    purposes = login("coffee").get("/products/purposes").json()
    assert purposes == [
        "Текущие расходы",
        "Кассовый разрыв",
        "Закупка товара",
        "Сезонные расходы",
        "Оборудование",
        "Ремонт",
        "Новая точка",
    ]


def test_purpose_picks_the_product(login):
    result = match(login("coffee"), {"purpose": "Оборудование"})
    assert result[0]["product"]["code"] == "INVESTMENT"
    assert result[0]["recommended"] and result[0]["notes"] == ["Подходит для цели «Оборудование»"]
    assert [r["recommended"] for r in result[1:]] == [False, False]
    assert result[1]["notes"] == ["Продукт для других целей"]


def test_lowest_rate_among_fitting(login):
    result = match(login("coffee"), {"purpose": "Кассовый разрыв", "amount": 2_000_000, "term_months": 12})
    assert [r["product"]["code"] for r in result] == ["WORKING_CAPITAL", "EXPRESS", "INVESTMENT"]
    assert result[0]["recommended"] and "Самая низкая ставка среди подходящих" in result[0]["notes"]
    assert result[1]["fits"] and not result[1]["recommended"]


def test_amount_and_term_outside_product(login):
    result = match(login("coffee"), {"purpose": "Закупка", "amount": 500_000, "term_months": 30})
    by_code = {r["product"]["code"]: r for r in result}
    assert by_code["EXPRESS"]["purpose_match"] and not by_code["EXPRESS"]["fits"]
    assert "Срок — от 3 до 24 мес." in by_code["EXPRESS"]["notes"]
    assert "Сумма 500 000 ₽ ниже минимума: продукт от 1 000 000 ₽ до 30 000 000 ₽" in by_code["WORKING_CAPITAL"]["notes"]
    assert not any(r["recommended"] for r in result)


def test_unknown_purpose_recommends_nothing(login):
    result = match(login("coffee"), {"purpose": "Покупка яхты"})
    assert not any(r["purpose_match"] or r["recommended"] for r in result)
    assert login("coffee").post("/products/match", {"purpose": ""}).status_code == 422
