class DomainError(Exception):
    """Ошибка бизнес-правила. Текст message показывается пользователю как есть."""

    def __init__(self, code: str, message: str, http_status: int = 409):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def not_found() -> DomainError:
    return DomainError("not_found", "Заявка не найдена", 404)
