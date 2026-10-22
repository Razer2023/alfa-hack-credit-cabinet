---
to: B-integrations
from: A
story: S3.1, S4.1, S4.2
priority: normal
status: in_progress
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
- [ ] Dockerfile. Сервис в compose называется **`integrations`**, порт **8000** внутри контейнера: ядро уже ходит на `http://integrations:8000` (`CORE_INTEGRATIONS_URL`). `docker-compose.yml` обновлю я и переключу `CORE_INTEGRATIONS_MODE=http`
- [ ] `GET /health` → 200, для healthcheck в compose
- [ ] CI: `.github/workflows/integrations.yml` с задачей `name: integrations-test` (тесты на каждом PR). Я добавлю её в обязательные проверки. Образец — `.github/workflows/core.yml`
- [ ] Проверка совместимости: запусти ядро с `CORE_INTEGRATIONS_MODE=http CORE_INTEGRATIONS_URL=http://localhost:<порт>` и пройди три демо-сценария в Swagger ядра (заполнение по ИНН, проверка, решение)

## Пока не сделано, я работаю так
На встроенной заглушке, демо работает и без сервиса.

## Ответ владельца области

Принято. Сначала S3.1: `GET /api/v1/companies/{inn}/profile`, `GET /health`, три демо-ИНН в `data/synthetic/companies.json` (те же значения, что в заглушке ядра). `POST /api/v1/checks` (S4.1, S4.2) — следующим шагом.

Образ собирается из корня репозитория: `docker build -f services/integrations/Dockerfile .` В `docker-compose.yml` сервис не добавлял — это остаётся за ядром, вместе с `CORE_INTEGRATIONS_MODE=http`.

Стек как у ядра: FastAPI, Uvicorn, uv. Новых библиотек сверх `THIRD_PARTY_NOTICES` нет; для тестов — pytest, httpx, PyYAML.
