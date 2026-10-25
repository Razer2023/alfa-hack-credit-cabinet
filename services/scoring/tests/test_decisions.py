"""Кредитная логика: демо-сценарии, стоп-факторы, ручное рассмотрение, контрпредложения."""

import pytest
from conftest import TODAY, make_request

from app.calc import annuity_payment
from app.engine import decide
from app.schemas import DecisionIn


def run(rules, *args, **kwargs) -> dict:
    return decide(DecisionIn.model_validate(make_request(*args, **kwargs)), rules, TODAY)


def codes(result: dict) -> list[str]:
    return [r["code"] for r in result["reasons"]]


# --- Демо-сценарии из ТЗ ---


def test_demo_coffee_approved(rules):
    r = run(rules, "7701234567", "EXPRESS", 2_000_000, 12)
    assert r["result"] == "APPROVE" and r["risk_class"] == "A"
    assert r["offers"] == [{"amount": 2_000_000, "term_months": 12, "rate": 21.5}]
    assert r["reasons"] == []


def test_demo_stroy_counter_offer(rules):
    r = run(rules, "7702345678", "WORKING_CAPITAL", 10_000_000, 12)
    assert r["result"] == "COUNTER_OFFER"
    [offer] = r["offers"]
    assert offer["amount"] < 10_000_000 and offer["term_months"] == 36
    assert "PAYMENT_TOO_HIGH" in codes(r)


def test_demo_vector_manual_review(rules):
    r = run(rules, "7703456789", "WORKING_CAPITAL", 3_000_000, 12)
    assert r["result"] == "MANUAL_REVIEW" and r["offers"] == []
    assert codes(r) == ["BKI_OVERDUE"] and "45 дн." in r["reasons"][0]["text"]


# --- Инварианты ---


@pytest.mark.parametrize("inn", ["7701234567", "7702345678"])
@pytest.mark.parametrize("amount", [1_000_000, 3_000_000, 8_000_000, 20_000_000, 30_000_000])
@pytest.mark.parametrize("term", [6, 12, 24, 36])
def test_offers_respect_product_and_dscr(rules, inn, amount, term):
    r = run(rules, inn, "WORKING_CAPITAL", amount, term)
    product = rules.catalog.get("WORKING_CAPITAL")
    metrics = r["metrics"]
    budget = metrics["monthly_free_cash_flow"] / metrics["min_dscr"] - metrics["existing_debt_payment"]
    for offer in r["offers"]:
        assert product.min_amount <= offer["amount"] <= min(product.max_amount, metrics["limit"])
        assert product.min_term_months <= offer["term_months"] <= product.max_term_months
        assert annuity_payment(offer["amount"], offer["term_months"], offer["rate"]) <= budget
    if r["result"] == "APPROVE":
        assert r["offers"][0]["amount"] == amount and r["offers"][0]["term_months"] == term
    if r["result"] == "COUNTER_OFFER":
        assert len(r["offers"]) == 1 and r["reasons"]


def test_score_is_sum_of_factors(rules):
    r = run(rules, "7702345678", "WORKING_CAPITAL", 10_000_000, 12)
    assert r["score"] == rules.scorecard.base_score + sum(f["impact"] for f in r["factors"])
    assert {f["code"] for f in r["factors"]} == set(rules.scorecard.factors)


def test_model_version_from_config(rules):
    assert run(rules, "7701234567", "EXPRESS", 2_000_000, 12)["model_version"] == rules.model_version


# --- Стоп-факторы ---


def test_liquidation_rejected(rules):
    r = run(rules, "7701234567", "EXPRESS", 2_000_000, 12, egrul={"liquidation": True})
    assert r["result"] == "REJECT" and codes(r) == ["EGRUL_INACTIVE"]


def test_young_business_rejected(rules):
    r = run(rules, "7701234567", "EXPRESS", 2_000_000, 12, company={"registration_date": "2026-07-01"})
    assert r["result"] == "REJECT" and codes(r) == ["BUSINESS_TOO_YOUNG"]


def test_critical_overdue_rejected(rules):
    r = run(rules, "7701234567", "EXPRESS", 2_000_000, 12, bki={"max_overdue_days": 120})
    assert r["result"] == "REJECT" and codes(r) == ["BKI_OVERDUE_CRITICAL"]


def test_below_product_min_rejected(rules):
    r = run(rules, "7701234567", "WORKING_CAPITAL", 500_000, 12)
    assert r["result"] == "REJECT" and codes(r) == ["BELOW_PRODUCT_MIN"]
    assert "1 000 000" in r["reasons"][0]["text"]


# --- Ручное рассмотрение ---


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"fns": {"tax_debt": 50_000}}, "TAX_DEBT"),
        ({"fns": {"mass_address": True}}, "MASS_ADDRESS"),
        ({"company": {"revenue_year": None, "avg_monthly_turnover": None}}, "NO_REVENUE_DATA"),
    ],
)
def test_manual_triggers(rules, override, reason):
    r = run(rules, "7701234567", "EXPRESS", 2_000_000, 12, **override)
    assert r["result"] == "MANUAL_REVIEW" and reason in codes(r)


def test_missing_bki_goes_to_manual(rules):
    request = make_request("7701234567", "EXPRESS", 2_000_000, 12)
    request["enrichment"]["bki"] = None
    r = decide(DecisionIn.model_validate(request), rules, TODAY)
    assert r["result"] == "MANUAL_REVIEW" and codes(r) == ["NO_BKI_DATA"]


def test_low_score_rejected(rules):
    # Молодой маленький бизнес с высокой нагрузкой и короткой просрочкой
    r = run(
        rules, "7701234567", "EXPRESS", 3_000_000, 12,
        company={"registration_date": "2025-12-01", "revenue_year": 5_000_000, "employees": 2},
        bki={"max_overdue_days": 10, "active_loans": 5, "total_debt": 3_000_000},
    )
    assert r["risk_class"] == "D" and r["result"] == "REJECT" and codes(r) == ["LOW_SCORE"]
    # S6.3: клиент видит, что сильнее всего снизило оценку, — два худших фактора по баллам
    text = r["reasons"][0]["text"]
    assert "Сильнее всего на оценку повлияли: высокая долговая нагрузка, сумма кредита велика относительно выручки" in text


# --- Контрпредложения ---


def test_amount_over_product_max_capped(rules):
    r = run(rules, "7701234567", "EXPRESS", 7_000_000, 12)
    assert r["result"] == "COUNTER_OFFER" and "AMOUNT_OVER_PRODUCT" in codes(r)
    assert r["offers"][0]["amount"] <= 5_000_000


def test_amount_over_revenue_limit(rules):
    r = run(rules, "7701234567", "WORKING_CAPITAL", 9_000_000, 36)
    assert r["result"] == "COUNTER_OFFER" and "AMOUNT_OVER_LIMIT" in codes(r)
    assert r["offers"][0]["amount"] <= r["metrics"]["limit"]


def test_same_amount_longer_term_preferred(rules):
    r = run(rules, "7702345678", "WORKING_CAPITAL", 5_000_000, 12)
    assert r["result"] == "COUNTER_OFFER"
    assert r["offers"][0]["amount"] == 5_000_000 and r["offers"][0]["term_months"] % 6 == 0


def test_cannot_afford_min_rejected(rules):
    r = run(rules, "7702345678", "INVESTMENT", 3_000_000, 12, company={"avg_monthly_turnover": 600_000})
    assert r["result"] == "REJECT" and codes(r) == ["CANNOT_AFFORD_MIN"]


# --- Согласованность контрпредложения (предоценка спрашивает максимум продукта) ---


def test_counter_offer_does_not_depend_on_overasking(rules):
    """Сколько бы клиент ни попросил сверх возможного, предложение одно и то же — по классу предлагаемой суммы."""
    asked_10m = run(rules, "7702345678", "WORKING_CAPITAL", 10_000_000, 12)
    asked_max = run(rules, "7702345678", "WORKING_CAPITAL", 30_000_000, 36)
    assert asked_max["risk_class"] == "B"  # запрос 30 млн портит фактор «сумма к выручке»
    assert asked_max["offers"] == asked_10m["offers"] == [{"amount": 6_600_000, "term_months": 36, "rate": 18.9}]


def test_rescored_offer_passes_offer_check(rules):
    from app.engine import check_offer
    from app.schemas import OfferCheckIn

    for amount, term in [(30_000_000, 36), (20_000_000, 24), (10_000_000, 12)]:
        [offer] = run(rules, "7702345678", "WORKING_CAPITAL", amount, term)["offers"]
        request = make_request("7702345678", "WORKING_CAPITAL", amount, term) | {"terms": offer}
        assert check_offer(OfferCheckIn.model_validate(request), rules, TODAY)["allowed"], (amount, offer)
