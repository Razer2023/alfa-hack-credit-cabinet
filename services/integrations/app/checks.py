"""Полнота и корректность заявки (S4.1) и обогащение из моков (S4.2).

Пустые обязательные поля отвечают теми же текстами, что заглушка ядра:
ядро показывает их клиенту и переводит заявку в NEED_INFO.
"""

from app.enrichment import enrichment_for

REQUIRED = (
    ("amount", "Укажите сумму кредита"),
    ("term_months", "Укажите срок кредита"),
    ("purpose", "Укажите цель кредита"),
)

INVALID = {
    "amount": "Сумма кредита должна быть целым числом больше нуля",
    "term_months": "Срок кредита должен быть целым числом месяцев больше нуля",
}


def _empty_number(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (int, float)):
        return value == 0
    return False


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def missing_items(snapshot: dict) -> list[dict]:
    application = snapshot.get("application")
    if not isinstance(application, dict):
        application = {}

    missing: list[dict] = []
    for field, message in REQUIRED:
        value = application.get(field)
        if field == "purpose":
            if not isinstance(value, str) or not value.strip():
                missing.append({"field": field, "message": message})
            continue
        if _empty_number(value):
            missing.append({"field": field, "message": message})
        elif not _positive_int(value):
            missing.append({"field": field, "message": INVALID[field]})

    company = snapshot.get("company")
    if not isinstance(company, dict) or not company:
        missing.append({"field": "company", "message": "Заполните данные компании по ИНН"})

    inn = snapshot.get("inn")
    if not isinstance(inn, str) or not inn.strip():
        missing.append({"field": "inn", "message": "Укажите ИНН компании"})
    elif not (inn.isdigit() and len(inn) in (10, 12)):
        missing.append({"field": "inn", "message": "ИНН должен содержать 10 или 12 цифр"})
    return missing


def check_application(snapshot: dict) -> dict:
    missing = missing_items(snapshot)
    inn = snapshot.get("inn")
    return {
        "complete": not missing,
        "missing": missing,
        "enrichment": enrichment_for(inn if isinstance(inn, str) else ""),
    }
