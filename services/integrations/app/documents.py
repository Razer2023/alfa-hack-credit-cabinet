"""Запрос документов (S4.4) и их хранение (S4.7).

Ядро переводит заявку в NEED_INFO. Файл лежит здесь, а не в базе ядра.
Прототип пишет файлы на диск сервиса. Отдельный MinIO в корневой compose не добавлялся:
это файл области A.
"""

import json
import os
import threading
import uuid
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png"})
_lock = threading.Lock()


class DocumentError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def documents_dir() -> Path:
    override = os.environ.get("INTEGRATIONS_DOCUMENTS_DIR")
    path = Path(override) if override else Path(__file__).resolve().parents[1] / ".documents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _db_path() -> Path:
    return documents_dir() / "requests.json"


def _load() -> dict[str, dict]:
    path = _db_path()
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DocumentError(500, "storage_broken", "Хранилище запросов повреждено")
    return data


def _save(data: dict[str, dict]) -> None:
    _db_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _inn_ok(inn: object) -> bool:
    return isinstance(inn, str) and inn.isdigit() and len(inn) in (10, 12)


def _code_ok(code: object) -> bool:
    return isinstance(code, str) and code.isidentifier() and code.islower() and len(code) <= 40


def _safe_filename(name: str) -> str:
    base = Path(name).name.replace("\\", "_").replace("/", "_")
    cleaned = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in base)
    return (cleaned.strip("._") or "document")[:80]


def _refresh_status(request: dict) -> None:
    waiting = any(item["status"] != "RECEIVED" for item in request["items"])
    request["status"] = "OPEN" if waiting else "COMPLETE"


def create_request(body: dict) -> dict:
    application_id = body.get("application_id")
    if not isinstance(application_id, str) or not application_id.strip():
        raise DocumentError(400, "invalid", "Укажите application_id")
    if not _inn_ok(body.get("inn")):
        raise DocumentError(400, "invalid", "ИНН должен содержать 10 или 12 цифр")
    raw_items = body.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise DocumentError(400, "invalid", "Укажите хотя бы один документ")

    items: list[dict] = []
    seen: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise DocumentError(400, "invalid", "Пункт запроса должен быть объектом")
        code = raw.get("code")
        title = raw.get("title")
        if not _code_ok(code):
            raise DocumentError(400, "invalid", "Код документа: латиница в нижнем регистре, до 40 символов")
        if not isinstance(title, str) or not title.strip():
            raise DocumentError(400, "invalid", "Укажите название документа")
        if code in seen:
            raise DocumentError(400, "invalid", "Коды документов в одном запросе не повторяются")
        seen.add(code)
        items.append(
            {
                "code": code,
                "title": title.strip(),
                "status": "WAITING",
                "filename": None,
                "content_type": None,
                "size": None,
            }
        )

    comment = body.get("comment")
    if comment is not None and not isinstance(comment, str):
        raise DocumentError(400, "invalid", "Комментарий должен быть текстом")

    request = {
        "id": str(uuid.uuid4()),
        "application_id": application_id.strip(),
        "inn": body["inn"],
        "comment": comment.strip() if isinstance(comment, str) and comment.strip() else None,
        "status": "OPEN",
        "items": items,
    }
    with _lock:
        data = _load()
        data[request["id"]] = request
        _save(data)
    return request


def list_requests(application_id: str | None) -> list[dict]:
    with _lock:
        data = _load()
    rows = list(data.values())
    if application_id:
        rows = [row for row in rows if row["application_id"] == application_id]
    return rows


def get_request(request_id: str) -> dict:
    with _lock:
        found = _load().get(request_id)
    if found is None:
        raise DocumentError(404, "not_found", "Запрос документов не найден")
    return found


def save_file(request_id: str, code: str, filename: str, content_type: str, payload: bytes) -> dict:
    media = content_type.split(";", 1)[0].strip().lower()
    if media not in ALLOWED_TYPES:
        raise DocumentError(400, "invalid", "Нужен файл PDF, JPEG или PNG")
    if not payload:
        raise DocumentError(400, "invalid", "Файл пустой")
    if len(payload) > MAX_BYTES:
        raise DocumentError(400, "invalid", "Файл больше 5 МБ")

    with _lock:
        data = _load()
        request = data.get(request_id)
        if request is None:
            raise DocumentError(404, "not_found", "Запрос документов не найден")
        item = next((row for row in request["items"] if row["code"] == code), None)
        if item is None:
            raise DocumentError(404, "not_found", "Такого документа в запросе нет")
        safe = _safe_filename(filename)
        folder = documents_dir() / "files" / request_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / code).write_bytes(payload)
        item["status"] = "RECEIVED"
        item["filename"] = safe
        item["content_type"] = media
        item["size"] = len(payload)
        _refresh_status(request)
        _save(data)
        return request


def read_file(request_id: str, code: str) -> tuple[bytes, str, str]:
    with _lock:
        request = _load().get(request_id)
        if request is None:
            raise DocumentError(404, "not_found", "Запрос документов не найден")
        item = next((row for row in request["items"] if row["code"] == code), None)
        if item is None or item["status"] != "RECEIVED":
            raise DocumentError(404, "not_found", "Файл ещё не загружен")
        payload = (documents_dir() / "files" / request_id / code).read_bytes()
        return payload, item["content_type"], item["filename"]
