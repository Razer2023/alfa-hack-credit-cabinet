"""Клиент сервиса B «Данные и интеграции»: профиль компании по ИНН и проверка заявки."""

from typing import Protocol

from app.clients import stub_data
from app.clients.base import ExternalNotFound, JsonHttpClient


class IntegrationsClient(Protocol):
    def company_profile(self, inn: str) -> dict:
        """{"inn": str, "fields": {имя_поля: {"value": ..., "source": "EGRUL" | "FNS" | "BANK_ACCOUNT"}}}"""

    def check_application(self, snapshot: dict) -> dict:
        """{"complete": bool, "missing": [{"field", "message"}], "enrichment": {"egrul", "fns", "bki"}}"""


class HttpIntegrationsClient:
    def __init__(self, base_url: str, timeout: float):
        self._client = JsonHttpClient("integrations", base_url, timeout)

    def company_profile(self, inn: str) -> dict:
        return self._client.request("GET", f"/api/v1/companies/{inn}/profile")

    def check_application(self, snapshot: dict) -> dict:
        return self._client.request("POST", "/api/v1/checks", json=snapshot)


class StubIntegrationsClient:
    """Временная заглушка до готовности сервиса B."""

    REQUIRED = {
        "amount": "Укажите сумму кредита",
        "term_months": "Укажите срок кредита",
        "purpose": "Укажите цель кредита",
    }

    def company_profile(self, inn: str) -> dict:
        company = stub_data.COMPANIES.get(inn)
        if company is None:
            raise ExternalNotFound(inn)
        fields = {name: {"value": value, "source": source} for name, (value, source) in company.items()}
        return {"inn": inn, "fields": fields}

    def check_application(self, snapshot: dict) -> dict:
        application = snapshot["application"]
        missing = [
            {"field": field, "message": message}
            for field, message in self.REQUIRED.items()
            if not application.get(field)
        ]
        if not snapshot.get("company"):
            missing.append({"field": "company", "message": "Заполните данные компании по ИНН"})

        inn = snapshot["inn"]
        enrichment = {
            "egrul": {"status": "ACTIVE", "liquidation": False},
            "fns": {"tax_debt": 0, "mass_address": False},
            "bki": stub_data.CREDIT_HISTORY.get(inn, {"max_overdue_days": 0, "active_loans": 0, "total_debt": 0}),
        }
        return {"complete": not missing, "missing": missing, "enrichment": enrichment}
