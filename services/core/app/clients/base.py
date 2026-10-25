from typing import Any

import httpx


class ExternalServiceError(Exception):
    """Внешний сервис недоступен или ответил ошибкой. Шаг конвейера будет повторён позже."""


class ExternalNotFound(Exception):
    """Внешний сервис не нашёл объект (например, компанию по ИНН)."""


class ExternalRejected(Exception):
    """Внешний сервис отклонил запрос (400): message написан для человека, например «Файл больше 5 МБ»."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class JsonHttpClient:
    def __init__(self, service: str, base_url: str, timeout: float):
        self._service = service
        # Сервисы B и C — внутренние: HTTP_PROXY из окружения к ним не применяем,
        # иначе корпоративный прокси получит запросы к «scoring:8000» и ответит ошибкой
        self._http = httpx.Client(base_url=base_url, timeout=timeout, trust_env=False)

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        return self.raw(method, path, **kwargs).json()

    def raw(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"{self._service}: {exc}") from exc
        if response.status_code == 404:
            raise ExternalNotFound(f"{self._service}: {path}")
        if response.status_code == 400:
            try:
                message = response.json().get("message")
            except ValueError:
                message = None
            raise ExternalRejected(message or "Запрос отклонён")
        if response.status_code >= 400:
            raise ExternalServiceError(f"{self._service}: HTTP {response.status_code} {path}")
        return response
