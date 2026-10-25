"""Клиент сервиса B «Данные и интеграции»: профиль компании по ИНН, проверка заявки, документы."""

import copy
import uuid
from typing import Protocol

from app.clients import stub_data
from app.clients.base import ExternalNotFound, ExternalRejected, JsonHttpClient


class IntegrationsClient(Protocol):
    def company_profile(self, inn: str) -> dict:
        """{"inn": str, "fields": {имя_поля: {"value": ..., "source": "EGRUL" | "FNS" | "BANK_ACCOUNT"}}}"""

    def check_application(self, snapshot: dict) -> dict:
        """{"complete": bool, "missing": [{"field", "message"}], "enrichment": {"egrul", "fns", "bki"}}"""

    # Документы (S4.4, S4.7). Запрос: {"id", "application_id", "inn", "comment", "status": OPEN|COMPLETE,
    # "items": [{"code", "title", "status": WAITING|RECEIVED, "filename", "content_type", "size"}]}

    def create_document_request(self, body: dict) -> dict: ...

    def list_document_requests(self, application_id: str) -> list[dict]: ...

    def dashboard_applications(self) -> list[dict]: ...

    def upload_document(self, request_id: str, code: str, filename: str, content_type: str, payload: bytes) -> dict: ...

    def download_document(self, request_id: str, code: str) -> tuple[bytes, str, str]:
        """(содержимое, content-type, имя файла)"""


class HttpIntegrationsClient:
    def __init__(self, base_url: str, timeout: float):
        self._client = JsonHttpClient("integrations", base_url, timeout)

    def company_profile(self, inn: str) -> dict:
        return self._client.request("GET", f"/api/v1/companies/{inn}/profile")

    def check_application(self, snapshot: dict) -> dict:
        return self._client.request("POST", "/api/v1/checks", json=snapshot)

    def create_document_request(self, body: dict) -> dict:
        return self._client.request("POST", "/api/v1/document-requests", json=body)

    def list_document_requests(self, application_id: str) -> list[dict]:
        return self._client.request("GET", "/api/v1/document-requests", params={"application_id": application_id})

    def dashboard_applications(self) -> list[dict]:
        return self._client.request("GET", "/api/v1/dashboard/applications")

    def upload_document(self, request_id: str, code: str, filename: str, content_type: str, payload: bytes) -> dict:
        # Имя файла в заголовке — ASCII: сервис B всё равно приводит его к безопасному виду
        headers = {"Content-Type": content_type, "X-Filename": filename.encode("ascii", "replace").decode()}
        path = f"/api/v1/document-requests/{request_id}/items/{code}"
        return self._client.request("POST", path, content=payload, headers=headers)

    def download_document(self, request_id: str, code: str) -> tuple[bytes, str, str]:
        response = self._client.raw("GET", f"/api/v1/document-requests/{request_id}/items/{code}/file")
        disposition = response.headers.get("content-disposition", "")
        filename = disposition.split("filename=")[-1].strip('"') if "filename=" in disposition else code
        return response.content, response.headers.get("content-type", "application/octet-stream"), filename


class StubDocuments:
    """Документы в памяти — для тестов ядра и разработки без сервиса B. Правила как у B: PDF/JPEG/PNG, до 5 МБ."""

    ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
    MAX_BYTES = 5 * 1024 * 1024

    def __init__(self):
        self._requests: dict[str, dict] = {}
        self._files: dict[tuple[str, str], bytes] = {}

    def create_document_request(self, body: dict) -> dict:
        items = [
            {"code": i["code"], "title": i["title"], "status": "WAITING", "filename": None, "content_type": None, "size": None}
            for i in body["items"]
        ]
        request = {
            "id": str(uuid.uuid4()),
            "application_id": body["application_id"],
            "inn": body["inn"],
            "comment": body.get("comment"),
            "status": "OPEN",
            "items": items,
        }
        self._requests[request["id"]] = request
        return copy.deepcopy(request)

    def list_document_requests(self, application_id: str) -> list[dict]:
        return [copy.deepcopy(r) for r in self._requests.values() if r["application_id"] == application_id]

    def upload_document(self, request_id: str, code: str, filename: str, content_type: str, payload: bytes) -> dict:
        if content_type.split(";")[0].strip().lower() not in self.ALLOWED_TYPES:
            raise ExternalRejected("Нужен файл PDF, JPEG или PNG")
        if not payload or len(payload) > self.MAX_BYTES:
            raise ExternalRejected("Файл пустой или больше 5 МБ")
        request = self._requests.get(request_id)
        item = next((i for i in (request or {}).get("items", []) if i["code"] == code), None)
        if item is None:
            raise ExternalNotFound(f"{request_id}/{code}")
        item.update(status="RECEIVED", filename=filename, content_type=content_type, size=len(payload))
        request["status"] = "COMPLETE" if all(i["status"] == "RECEIVED" for i in request["items"]) else "OPEN"
        self._files[(request_id, code)] = payload
        return copy.deepcopy(request)

    def download_document(self, request_id: str, code: str) -> tuple[bytes, str, str]:
        if (request_id, code) not in self._files:
            raise ExternalNotFound(f"{request_id}/{code}")
        item = next(i for i in self._requests[request_id]["items"] if i["code"] == code)
        return self._files[(request_id, code)], item["content_type"], item["filename"]


class StubIntegrationsClient(StubDocuments):
    """Встроенная заглушка сервиса B: для тестов ядра и разработки без него."""

    REQUIRED = {
        "amount": "Укажите сумму кредита",
        "term_months": "Укажите срок кредита",
        "purpose": "Укажите цель кредита",
    }

    def dashboard_applications(self) -> list[dict]:
        return stub_data.DASHBOARD

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
