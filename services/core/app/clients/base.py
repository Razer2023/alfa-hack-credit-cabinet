from typing import Any

import httpx


class ExternalServiceError(Exception):
    """Внешний сервис недоступен или ответил ошибкой. Шаг конвейера будет повторён позже."""


class ExternalNotFound(Exception):
    """Внешний сервис не нашёл объект (например, компанию по ИНН)."""


class JsonHttpClient:
    def __init__(self, service: str, base_url: str, timeout: float):
        self._service = service
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"{self._service}: {exc}") from exc
        if response.status_code == 404:
            raise ExternalNotFound(f"{self._service}: {path}")
        if response.status_code >= 400:
            raise ExternalServiceError(f"{self._service}: HTTP {response.status_code} {path}")
        return response.json()
