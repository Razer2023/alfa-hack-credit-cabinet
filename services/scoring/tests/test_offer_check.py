"""S5.4: проверка условий, которые вписал сотрудник банка."""

import pytest
from conftest import TODAY, make_request

from app.calc import annuity_payment
from app.engine import check_offer, decide
from app.schemas import DecisionIn, OfferCheckIn


def run(rules, inn, product, amount, term, rate=None, **overrides) -> dict:
    # Заявка клиента — как была подана, условия — то, что вписал сотрудник
    request = make_request(inn, product, amount, term, **overrides)
    request["terms"] = {"amount": amount, "term_months": term, "rate": rate}
    return check_offer(OfferCheckIn.model_validate(request), rules, TODAY)


def codes(result: dict) -> list[str]:
    return [c["code"] for c in result["checks"]]


def test_recommendation_always_passes(rules):
    """То, что рекомендовал скоринг, проверку проходит — иначе сотрудник не смог бы его подтвердить."""
    for inn, product, amount, term in [
        ("7701234567", "EXPRESS", 2_000_000, 12),
        ("7702345678", "WORKING_CAPITAL", 10_000_000, 12),
        ("7702345678", "WORKING_CAPITAL", 5_000_000, 12),
    ]:
        decision = decide(DecisionIn.model_validate(make_request(inn, product, amount, term)), rules, TODAY)
        [offer] = decision["offers"]
        r = run(rules, inn, product, offer["amount"], offer["term_months"], offer["rate"])
        assert r["allowed"], (inn, offer, r["checks"])
        assert r["checks"] == []


def test_manager_puts_full_amount_back(rules):
    """Главный сценарий S5.4: скоринг предложил 6,6 млн на 36 мес., менеджер вернул 10 млн на 12."""
    r = run(rules, "7702345678", "WORKING_CAPITAL", 10_000_000, 12)
    assert not r["allowed"]
    assert codes(r) == ["DSCR_TOO_LOW"]
    assert "0,46" in r["checks"][0]["text"]
    suggestion = r["suggestion"]
    assert suggestion["term_months"] == 12 and suggestion["amount"] < 10_000_000
    budget = r["metrics"]["monthly_free_cash_flow"] / 1.25 - r["metrics"]["existing_debt_payment"]
    assert annuity_payment(suggestion["amount"], 12, suggestion["rate"]) <= budget


def test_suggestion_passes_check(rules):
    first = run(rules, "7702345678", "WORKING_CAPITAL", 10_000_000, 12)
    s = first["suggestion"]
    assert run(rules, "7702345678", "WORKING_CAPITAL", s["amount"], s["term_months"], s["rate"])["allowed"]


def test_rate_defaults_to_risk_class(rules):
    r = run(rules, "7701234567", "EXPRESS", 2_000_000, 12)
    assert r["terms"]["rate"] == 21.5 and r["risk_class"] == "A"
    assert r["monthly_payment"] == annuity_payment(2_000_000, 12, 21.5)


@pytest.mark.parametrize(
    ("amount", "term", "rate", "code"),
    [
        (200_000, 12, None, "AMOUNT_BELOW_PRODUCT"),
        (6_000_000, 24, None, "AMOUNT_OVER_PRODUCT"),
        (2_000_000, 36, None, "TERM_OUT_OF_PRODUCT"),
        (2_000_000, 12, 15.0, "RATE_BELOW_MIN"),
    ],
)
def test_product_limits(rules, amount, term, rate, code):
    r = run(rules, "7701234567", "EXPRESS", amount, term, rate)
    assert not r["allowed"] and code in codes(r)


def test_revenue_limit(rules):
    # Кофейня, класс A: лимит 35 % от 24 млн = 8,4 млн
    r = run(rules, "7701234567", "WORKING_CAPITAL", 9_000_000, 36)
    assert "AMOUNT_OVER_LIMIT" in codes(r) and "8 400 000" in r["checks"][codes(r).index("AMOUNT_OVER_LIMIT")]["text"]
    assert r["suggestion"]["amount"] <= 8_400_000


def test_underwriter_class_uses_fallback_limit(rules):
    # Вектор Трейд — класс C, своего лимита нет, берётся лимит класса B (25 % от 18 млн)
    r = run(rules, "7703456789", "WORKING_CAPITAL", 3_000_000, 12)
    assert r["risk_class"] == "C" and r["metrics"]["limit"] == 4_500_000


def test_missing_data_is_warning_not_error(rules):
    r = run(rules, "7701234567", "EXPRESS", 2_000_000, 12, company={"revenue_year": None, "avg_monthly_turnover": None})
    assert r["allowed"]
    assert r["checks"] == [{"code": "NO_FINANCIAL_DATA", "level": "warning", "text": r["checks"][0]["text"]}]
    assert r["suggestion"] is None


def test_api(api):
    request = make_request("7702345678", "WORKING_CAPITAL", 10_000_000, 12)
    request["terms"] = {"amount": 10_000_000, "term_months": 12}
    body = api.post("/api/v1/offers/check", json=request).json()
    assert body["allowed"] is False and body["checks"][0]["code"] == "DSCR_TOO_LOW"
    assert body["model_version"].startswith("scorecard-1.1")


def test_api_unknown_product(api):
    request = make_request("7701234567", "NOPE", 2_000_000, 12)
    request["terms"] = {"amount": 2_000_000, "term_months": 12}
    assert api.post("/api/v1/offers/check", json=request).status_code == 422
