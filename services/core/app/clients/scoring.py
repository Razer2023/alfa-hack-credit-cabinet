"""Клиент сервиса C «Скоринг и решение»: продукты, расчёт платежа, кредитное решение."""

from typing import Protocol

from app.clients import stub_data
from app.clients.base import ExternalNotFound, JsonHttpClient


class ScoringClient(Protocol):
    def list_products(self) -> list[dict]: ...

    def get_product(self, code: str) -> dict: ...

    def calc_payment(self, amount: int, term_months: int, rate: float) -> dict:
        """{"monthly_payment": int, "total_payment": int, "overpayment": int}"""

    def decide(self, request: dict) -> dict:
        """{"result": "APPROVE" | "COUNTER_OFFER" | "REJECT" | "MANUAL_REVIEW", "score", "risk_class",
        "model_version", "factors": [...], "reasons": [...], "offers": [{"amount", "term_months", "rate"}]}"""


class HttpScoringClient:
    def __init__(self, base_url: str, timeout: float):
        self._client = JsonHttpClient("scoring", base_url, timeout)

    def list_products(self) -> list[dict]:
        return self._client.request("GET", "/api/v1/products")

    def get_product(self, code: str) -> dict:
        return self._client.request("GET", f"/api/v1/products/{code}")

    def calc_payment(self, amount: int, term_months: int, rate: float) -> dict:
        body = {"amount": amount, "term_months": term_months, "rate": rate}
        return self._client.request("POST", "/api/v1/calc/payment", json=body)

    def decide(self, request: dict) -> dict:
        return self._client.request("POST", "/api/v1/decisions", json=request)


def annuity_payment(amount: int, term_months: int, rate: float) -> int:
    monthly = rate / 12 / 100
    if monthly == 0:
        return round(amount / term_months)
    return round(amount * monthly / (1 - (1 + monthly) ** -term_months))


class StubScoringClient:
    """Временная заглушка до готовности сервиса C. Логика нарочно простая: настоящие правила — в области C."""

    MAX_DEBT_TO_REVENUE = 0.25

    def list_products(self) -> list[dict]:
        return stub_data.PRODUCTS

    def get_product(self, code: str) -> dict:
        for product in stub_data.PRODUCTS:
            if product["code"] == code:
                return product
        raise ExternalNotFound(code)

    def calc_payment(self, amount: int, term_months: int, rate: float) -> dict:
        payment = annuity_payment(amount, term_months, rate)
        total = payment * term_months
        return {"monthly_payment": payment, "total_payment": total, "overpayment": total - amount}

    def decide(self, request: dict) -> dict:
        application = request["application"]
        product = self.get_product(application["product_code"])
        bki = request["enrichment"]["bki"]
        revenue = request["company"].get("revenue_year") or 0
        amount, term = application["amount"], application["term_months"]
        rate = product["base_rate"]
        base = {"model_version": "stub-1", "factors": [], "reasons": []}

        if bki["max_overdue_days"] > 30:
            return base | {
                "result": "MANUAL_REVIEW",
                "score": 480,
                "risk_class": "C",
                "reasons": [{"code": "BKI_OVERDUE", "text": f"Просрочка {bki['max_overdue_days']} дн. в БКИ"}],
                "offers": [],
            }

        limit = int(revenue * self.MAX_DEBT_TO_REVENUE // 100_000 * 100_000)
        if amount > limit:
            return base | {
                "result": "COUNTER_OFFER",
                "score": 640,
                "risk_class": "B",
                "reasons": [{"code": "AMOUNT_OVER_LIMIT", "text": "Запрошенная сумма выше допустимой по выручке"}],
                "offers": [{"amount": limit, "term_months": product["max_term_months"], "rate": rate}],
            }

        return base | {
            "result": "APPROVE",
            "score": 720,
            "risk_class": "A",
            "offers": [{"amount": amount, "term_months": term, "rate": rate}],
        }
