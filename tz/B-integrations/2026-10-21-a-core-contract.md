---
to: B-integrations
from: A
story: S3.1, S4.1, S4.2
priority: normal
status: new
done_in: ""
---

# Сервис integrations: что от него ждёт ядро

## Зачем
Ядро уже работает на встроенной заглушке (`services/core/app/clients/integrations.py`, `stub_data.py`). Нужен настоящий сервис с тем же контрактом: тогда ядро переключится на него одной переменной `CORE_INTEGRATIONS_MODE=http`.

## Что нужно сделать
Сервис в `services/integrations/` (стек на твой выбор), порт 8000 внутри контейнера, Dockerfile. Два эндпоинта.

### 1. Профиль компании по ИНН (S3.1)
```http
GET /api/v1/companies/{inn}/profile
```
```json
{
  "inn": "7701234567",
  "fields": {
    "name":                 {"value": "ООО «Кофейня на Лесной»", "source": "EGRUL"},
    "ogrn":                 {"value": "1207700123456", "source": "EGRUL"},
    "registration_date":    {"value": "2020-03-12", "source": "EGRUL"},
    "okved":                {"value": "56.10 — Деятельность ресторанов и кафе", "source": "EGRUL"},
    "address":              {"value": "г. Москва, ул. Лесная, д. 5", "source": "EGRUL"},
    "director":             {"value": "Иванова Мария Сергеевна", "source": "EGRUL"},
    "employees":            {"value": 12, "source": "FNS"},
    "tax_regime":           {"value": "УСН", "source": "FNS"},
    "revenue_year":         {"value": 24000000, "source": "BANK_ACCOUNT"},
    "avg_monthly_turnover": {"value": 2000000, "source": "BANK_ACCOUNT"}
  }
}
```
Компания не найдена → `404`. `source`: `EGRUL`, `FNS`, `BANK_ACCOUNT` (веб показывает его бейджем у поля). Поля можно добавлять; `revenue_year` нужен скорингу.

### 2. Проверка заявки и обогащение (S4.1, S4.2)
```http
POST /api/v1/checks
```
Запрос (ядро шлёт так):
```json
{
  "application_id": "uuid",
  "inn": "7701234567",
  "application": {"product_code": "EXPRESS", "amount": 2000000, "term_months": 12, "purpose": "Закупка товара"},
  "company": {"name": "ООО «Кофейня на Лесной»", "revenue_year": 24000000},
  "extra": {}
}
```
Ответ:
```json
{
  "complete": true,
  "missing": [{"field": "purpose", "message": "Укажите цель кредита"}],
  "enrichment": {
    "egrul": {"status": "ACTIVE", "liquidation": false},
    "fns":   {"tax_debt": 0, "mass_address": false},
    "bki":   {"max_overdue_days": 0, "active_loans": 1, "total_debt": 400000}
  }
}
```
Если `complete: false`, ядро переводит заявку в `NEED_INFO` и показывает клиенту `missing[].message`. `enrichment.bki` обязателен: по нему работает скоринг.

## Готово, когда
- [ ] Три демо-ИНН из `stub_data.py` отдают те же данные (или согласованные новые): на них держится демо
- [ ] Ошибки: 404 — не найдено, 5xx — сбой (ядро повторит шаг само)
- [ ] OpenAPI сервиса в `contracts/integrations.yaml`
- [ ] Dockerfile; имя сервиса и порт — в PR, `docker-compose.yml` обновлю я

## Пока не сделано, я работаю так
На встроенной заглушке, демо работает и без сервиса.

## Ответ владельца области
