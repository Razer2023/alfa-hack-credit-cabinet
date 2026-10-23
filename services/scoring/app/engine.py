"""Кредитное решение (S5.1, S5.2, S6.1) и проверка условий сотрудника банка (S5.4).

Порядок проверок — как в кредитном конвейере банка:
1. Стоп-факторы → отказ без расчётов.
2. Условия продукта (минимальная сумма).
3. Триггеры ручного рассмотрения → андеррайтер.
4. Балльная карта → класс риска: D — отказ, C — андеррайтер, A и B — автоматическое решение.
5. Для A и B — лимит по выручке и DSCR: одобрение запрошенных условий или контрпредложение.

Все числа берутся из rules/scorecard.yaml, здесь только порядок и арифметика.
"""

from dataclasses import dataclass
from datetime import date
from math import floor

from app.calc import annuity_payment, max_amount_for_payment
from app.rules import Product, RiskClass, Rules
from app.schemas import DecisionIn, OfferCheckIn

MIN_SCORE, MAX_SCORE = 300, 900


class UnknownProduct(Exception):
    pass


@dataclass
class Facts:
    """Значения факторов, посчитанные из заявки. None — данных нет."""

    business_age_years: float | None
    revenue: float | None
    monthly_turnover: float | None
    overdue_days: int | None
    active_loans: int | None
    total_debt: float | None
    employees: int | None
    tax_debt: float
    mass_address: bool
    egrul_status: str
    liquidation: bool
    amount: int

    @property
    def debt_load(self) -> float | None:
        if self.total_debt is None or not self.revenue:
            return None
        return self.total_debt / self.revenue

    @property
    def loan_to_revenue(self) -> float | None:
        return self.amount / self.revenue if self.revenue else None

    def value(self, code: str) -> float | None:
        return {
            "BUSINESS_AGE": self.business_age_years,
            "REVENUE": self.revenue,
            "BKI_OVERDUE": self.overdue_days,
            "ACTIVE_LOANS": self.active_loans,
            "DEBT_LOAD": self.debt_load,
            "LOAN_TO_REVENUE": self.loan_to_revenue,
            "EMPLOYEES": self.employees,
            "TAX_DEBT": self.tax_debt,
            "MASS_ADDRESS": float(self.mass_address),
        }[code]


def collect_facts(req: DecisionIn, today: date) -> Facts:
    company, enrichment = req.company, req.enrichment
    bki = enrichment.bki
    age = (today - company.registration_date).days / 365.25 if company.registration_date else None
    revenue = company.revenue_year or None
    turnover = company.avg_monthly_turnover or (revenue / 12 if revenue else None)
    return Facts(
        business_age_years=age,
        revenue=revenue,
        monthly_turnover=turnover,
        overdue_days=bki.max_overdue_days if bki else None,
        active_loans=bki.active_loans if bki else None,
        total_debt=bki.total_debt if bki else None,
        employees=company.employees,
        tax_debt=enrichment.fns.tax_debt,
        mass_address=enrichment.fns.mass_address,
        egrul_status=enrichment.egrul.status,
        liquidation=enrichment.egrul.liquidation,
        amount=req.application.amount,
    )


def _num(x: float) -> str:
    return f"{round(x):,}".replace(",", " ")


def _rub(x: float) -> str:
    return f"{_num(x)} ₽"


def format_value(unit: str, value: float | None) -> str:
    if value is None:
        return "нет данных"
    match unit:
        case "years":
            return f"{value:.1f}".replace(".", ",") + " г."
        case "rub":
            return _rub(value)
        case "days":
            return f"{int(value)} дн."
        case "share":
            return f"{value * 100:.1f}".replace(".", ",") + " %"
        case "flag":
            return "да" if value else "нет"
        case _:
            return str(int(value))


def score_factors(facts: Facts, rules: Rules) -> tuple[int, list[dict]]:
    card = rules.scorecard
    factors = []
    for code, factor in card.factors.items():
        value = facts.value(code)
        impact = 0 if value is None else factor.points(value)
        factors.append(
            {"code": code, "title": factor.title, "impact": impact, "value": format_value(factor.unit, value)}
        )
    score = card.base_score + sum(f["impact"] for f in factors)
    return max(MIN_SCORE, min(MAX_SCORE, score)), factors


def round_down(amount: float, step: int) -> int:
    return int(floor(amount / step) * step)


def decide(req: DecisionIn, rules: Rules, today: date | None = None) -> dict:
    today = today or date.today()
    card = rules.scorecard
    product = rules.catalog.get(req.application.product_code)
    if product is None:
        raise UnknownProduct(req.application.product_code)

    facts = collect_facts(req, today)
    score, factors = score_factors(facts, rules)
    risk = card.risk_class(score)
    metrics = _metrics(facts, req, product, risk, rules)
    base = {
        "score": score,
        "risk_class": risk.code,
        "model_version": rules.model_version,
        "factors": factors,
        "metrics": metrics,
    }

    def result(kind: str, reasons: list[dict], offers: list[dict] | None = None) -> dict:
        return base | {"result": kind, "reasons": reasons, "offers": offers or []}

    # 1. Стоп-факторы
    stop = card.stop_factors
    if facts.liquidation or facts.egrul_status not in stop.egrul_ok_statuses:
        return result("REJECT", [card.reason("EGRUL_INACTIVE")])
    if facts.business_age_years is not None and facts.business_age_years * 12 < stop.min_business_age_months:
        return result("REJECT", [card.reason("BUSINESS_TOO_YOUNG")])
    if facts.overdue_days is not None and facts.overdue_days > stop.max_overdue_days:
        return result("REJECT", [card.reason("BKI_OVERDUE_CRITICAL")])

    # 2. Условия продукта
    if req.application.amount < product.min_amount:
        reason = card.reason("BELOW_PRODUCT_MIN", product=product.name, min_amount=_num(product.min_amount))
        return result("REJECT", [reason])

    # 3. Триггеры ручного рассмотрения
    manual = card.manual_review
    triggers = []
    if facts.overdue_days is not None and facts.overdue_days >= manual.overdue_days_from:
        triggers.append(card.reason("BKI_OVERDUE", days=facts.overdue_days))
    if facts.tax_debt > manual.tax_debt_above:
        triggers.append(card.reason("TAX_DEBT"))
    if manual.mass_address and facts.mass_address:
        triggers.append(card.reason("MASS_ADDRESS"))
    if facts.revenue is None:
        triggers.append(card.reason("NO_REVENUE_DATA"))
    if facts.overdue_days is None:
        triggers.append(card.reason("NO_BKI_DATA"))
    if triggers:
        return result("MANUAL_REVIEW", triggers)

    # 4. Класс риска
    if risk.decision == "REJECT":
        return result("REJECT", [card.reason("LOW_SCORE")])
    if risk.decision == "MANUAL_REVIEW":
        return result("MANUAL_REVIEW", [card.reason("BORDERLINE_SCORE")])

    # 5. Лимит и DSCR
    return _affordable_offer(req, product, risk, metrics, rules, result)


def _metrics(facts: Facts, req: DecisionIn, product: Product, risk: RiskClass, rules: Rules) -> dict:
    aff = rules.scorecard.affordability
    out = {"limit": None, "monthly_free_cash_flow": None, "existing_debt_payment": None,
           "new_payment": None, "dscr": None, "min_dscr": aff.min_dscr}
    rate = product.base_rate + risk.rate_adjustment
    out["new_payment"] = annuity_payment(req.application.amount, req.application.term_months, rate)
    if facts.revenue and risk.limit_share:
        out["limit"] = round_down(facts.revenue * risk.limit_share, aff.amount_step)
    if facts.monthly_turnover is not None and facts.total_debt is not None:
        fcf = facts.monthly_turnover * aff.free_cash_flow_share
        existing = facts.total_debt * aff.existing_debt_monthly_share
        out["monthly_free_cash_flow"] = round(fcf)
        out["existing_debt_payment"] = round(existing)
        out["dscr"] = round(fcf / (existing + out["new_payment"]), 2)
    return out


def _affordable_offer(req, product: Product, risk: RiskClass, metrics: dict, rules: Rules, result) -> dict:
    card = rules.scorecard
    aff = card.affordability
    amount, term = req.application.amount, req.application.term_months
    rate = round(product.base_rate + risk.rate_adjustment, 2)
    # Сколько в месяц компания может платить по новому кредиту, сохраняя DSCR не ниже минимума
    budget = metrics["monthly_free_cash_flow"] / aff.min_dscr - metrics["existing_debt_payment"]

    def fits(a: int, t: int) -> bool:
        return annuity_payment(a, t, rate) <= budget

    reasons = []
    cap = min(product.max_amount, metrics["limit"])
    if amount > product.max_amount:
        reasons.append(card.reason("AMOUNT_OVER_PRODUCT", product=product.name, max_amount=_num(product.max_amount)))
    elif amount > metrics["limit"]:
        reasons.append(card.reason("AMOUNT_OVER_LIMIT"))
    clamped_term = min(max(term, product.min_term_months), product.max_term_months)
    if clamped_term != term:
        reasons.append(card.reason("TERM_ADJUSTED"))

    offer_amount = min(amount, cap)
    if not reasons and fits(amount, term):
        return result("APPROVE", [], [{"amount": amount, "term_months": term, "rate": rate}])

    if not fits(offer_amount, clamped_term):
        reasons.append(card.reason("PAYMENT_TOO_HIGH"))

    # Сначала та же сумма на минимально достаточный срок — клиент получает нужные деньги.
    # Срок контрпредложения — кратный term_step, как в типовых условиях банка
    step = aff.term_step
    longer = range((clamped_term // step + 1) * step, product.max_term_months, step)
    for t in (clamped_term, *longer, product.max_term_months):
        if fits(offer_amount, t):
            return result("COUNTER_OFFER", reasons, [{"amount": offer_amount, "term_months": t, "rate": rate}])

    # Иначе — максимальная сумма, которую компания потянет на максимальный срок
    max_term = product.max_term_months
    affordable = round_down(min(cap, max_amount_for_payment(budget, max_term, rate)), aff.amount_step)
    if affordable < product.min_amount:
        return result("REJECT", [card.reason("CANNOT_AFFORD_MIN")])
    return result("COUNTER_OFFER", reasons, [{"amount": affordable, "term_months": max_term, "rate": rate}])


def check_offer(req: OfferCheckIn, rules: Rules, today: date | None = None) -> dict:
    """S5.4: проходят ли условия, которые вписал сотрудник банка, кредитную политику.

    Проверяются те же ограничения, что при автоматическом контрпредложении:
    рамки продукта, минимальная ставка, лимит по выручке и DSCR.
    Решение, можно ли подтвердить условия с ошибками (например, андеррайтеру с комментарием), принимает ядро.
    """
    today = today or date.today()
    card = rules.scorecard
    product = rules.catalog.get(req.application.product_code)
    if product is None:
        raise UnknownProduct(req.application.product_code)

    terms = req.terms
    facts = collect_facts(req, today)
    facts.amount = terms.amount  # фактор «сумма к выручке» — по условиям сотрудника
    score, _ = score_factors(facts, rules)
    risk = card.risk_class(score)
    rate = terms.rate if terms.rate is not None else round(product.base_rate + risk.rate_adjustment, 2)
    payment = annuity_payment(terms.amount, terms.term_months, rate)

    checks: list[dict] = []
    if terms.amount < product.min_amount:
        checks.append(card.offer_check("AMOUNT_BELOW_PRODUCT", min_amount=_num(product.min_amount)))
    if terms.amount > product.max_amount:
        checks.append(card.offer_check("AMOUNT_OVER_PRODUCT", max_amount=_num(product.max_amount)))
    if not product.min_term_months <= terms.term_months <= product.max_term_months:
        checks.append(card.offer_check(
            "TERM_OUT_OF_PRODUCT", min_term=product.min_term_months, max_term=product.max_term_months))
    min_rate = round(product.base_rate + card.best_rate_adjustment, 2)
    if rate < min_rate:
        checks.append(card.offer_check("RATE_BELOW_MIN", min_rate=f"{min_rate:g}".replace(".", ",")))

    aff = card.affordability
    share = risk.limit_share or card.manual_offer.fallback_limit_share
    limit = round_down(facts.revenue * share, aff.amount_step) if facts.revenue else None
    if limit is not None and terms.amount > limit:
        checks.append(card.offer_check("AMOUNT_OVER_LIMIT", limit=_num(limit)))

    metrics = {"limit": limit, "monthly_free_cash_flow": None, "existing_debt_payment": None,
               "new_payment": payment, "dscr": None, "min_dscr": aff.min_dscr}
    budget = None
    if facts.monthly_turnover is not None and facts.total_debt is not None:
        fcf = facts.monthly_turnover * aff.free_cash_flow_share
        existing = facts.total_debt * aff.existing_debt_monthly_share
        budget = fcf / aff.min_dscr - existing
        dscr = round(fcf / (existing + payment), 2)
        metrics |= {"monthly_free_cash_flow": round(fcf), "existing_debt_payment": round(existing), "dscr": dscr}
        if dscr < aff.min_dscr:
            checks.append(card.offer_check(
                "DSCR_TOO_LOW", dscr=f"{dscr:.2f}".replace(".", ","), min_dscr=f"{aff.min_dscr:g}".replace(".", ",")))
    else:
        checks.append(card.offer_check("NO_FINANCIAL_DATA", level="warning"))

    suggestion = None
    amount_problem = {"AMOUNT_OVER_PRODUCT", "AMOUNT_OVER_LIMIT", "DSCR_TOO_LOW"} & {c["code"] for c in checks}
    if amount_problem and budget is not None:
        caps = [product.max_amount, max_amount_for_payment(budget, terms.term_months, rate)]
        if limit is not None:
            caps.append(limit)
        best = round_down(min(caps), aff.amount_step)
        if best >= product.min_amount:
            suggestion = {"amount": best, "term_months": terms.term_months, "rate": rate}

    return {
        "allowed": not any(c["level"] == "error" for c in checks),
        "terms": {"amount": terms.amount, "term_months": terms.term_months, "rate": rate},
        "monthly_payment": payment,
        "checks": checks,
        "suggestion": suggestion,
        "score": score,
        "risk_class": risk.code,
        "model_version": rules.model_version,
        "metrics": metrics,
    }
