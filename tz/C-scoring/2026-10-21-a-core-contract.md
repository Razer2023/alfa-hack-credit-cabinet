---
to: C-scoring
from: A
story: S1.1, S3.2, S5.1, S5.2, S6.1
priority: normal
status: done
done_in: "#13"
---

# Сервис scoring: что от него ждёт ядро

## Зачем
Ядро уже работает на встроенной заглушке (`services/core/app/clients/scoring.py`, `stub_data.py`). Логика там нарочно примитивная. Настоящие продукты, скоринговая карта и кредитная логика — твоя область. Когда сервис готов, ядро переключится одной переменной `CORE_SCORING_MODE=http`.

## Что нужно сделать
Сервис в `services/scoring/`, порт 8000 внутри контейнера, Dockerfile. Четыре эндпоинта.

### 1. Каталог продуктов (S1.1)
```http
GET /api/v1/products
GET /api/v1/products/{code}        → 404, если нет
```
```json
{"code": "EXPRESS", "name": "Экспресс-кредит", "description": "...",
 "min_amount": 300000, "max_amount": 5000000, "min_term_months": 3, "max_term_months": 24, "base_rate": 22.5}
```

### 2. Расчёт платежа (S3.2)
```http
POST /api/v1/calc/payment
{"amount": 1200000, "term_months": 12, "rate": 22.5}
→ {"monthly_payment": 112602, "total_payment": 1351224, "overpayment": 151224}
```

### 3. Кредитное решение (S5.1, S5.2, S6.1)
```http
POST /api/v1/decisions
```
Запрос — снимок заявки плюс данные проверок от сервиса B:
```json
{
  "application_id": "uuid",
  "inn": "7702345678",
  "application": {"product_code": "WORKING_CAPITAL", "amount": 10000000, "term_months": 12, "purpose": "..."},
  "company": {"revenue_year": 30000000, "registration_date": "2018-06-01", "employees": 35},
  "extra": {},
  "enrichment": {"egrul": {...}, "fns": {...}, "bki": {"max_overdue_days": 0, "active_loans": 2, "total_debt": 3500000}}
}
```
Ответ:
```json
{
  "result": "COUNTER_OFFER",
  "score": 640,
  "risk_class": "B",
  "model_version": "scorecard-1.0",
  "factors": [{"code": "BUSINESS_AGE", "title": "Возраст бизнеса", "impact": 40}],
  "reasons": [{"code": "AMOUNT_OVER_LIMIT", "text": "Запрошенная сумма выше допустимой по выручке"}],
  "offers": [{"amount": 7500000, "term_months": 36, "rate": 19.9}]
}
```
- `result`: `APPROVE` | `COUNTER_OFFER` | `REJECT` | `MANUAL_REVIEW`.
- `offers`: для `APPROVE` — одно предложение (обычно = запросу), для `COUNTER_OFFER` — одно или несколько, для остальных пусто. Платёж ядро посчитает само через `/calc/payment`.
- `reasons[].text` клиент увидит как причину решения (S6.3), пиши человеческим языком.
- `factors` и `score` видит андеррайтер в карточке.

## Готово, когда
- [ ] Демо-компании дают три разных исхода: `7701234567` — одобрение, `7702345678` при 10 млн — контрпредложение, `7703456789` — ручное рассмотрение
- [ ] Правила в конфиге с версией (`model_version` в ответе), а не размазаны по коду
- [ ] OpenAPI сервиса в `contracts/scoring.yaml`
- [ ] Dockerfile. Сервис в compose называется **`scoring`**, порт **8000** внутри контейнера: ядро уже ходит на `http://scoring:8000` (`CORE_SCORING_URL`). `docker-compose.yml` обновлю я и переключу `CORE_SCORING_MODE=http`
- [ ] `GET /health` → 200, для healthcheck в compose
- [ ] CI: `.github/workflows/scoring.yml` с задачей `name: scoring-test` (тесты на каждом PR). Я добавлю её в обязательные проверки. Образец — `.github/workflows/core.yml`
- [ ] Проверка совместимости: запусти ядро с `CORE_SCORING_MODE=http CORE_SCORING_URL=http://localhost:<порт>` и пройди три демо-сценария в Swagger ядра

## Пока не сделано, я работаю так
На встроенной заглушке, демо работает и без сервиса.

## Ответ владельца области
Принято, сделано в ветке `feat/c-s5.1-scoring-service`. Сервис в `services/scoring/`, правила в `rules/*.yaml`, методика в `services/scoring/README.md`.

- Формат запроса и ответа — как в ТЗ. В ответе два дополнительных поля, ядро их просто сохранит: `factors[].value` (значение фактора для карточки андеррайтера, например «8,4 г.») и `metrics` (лимит, свободный поток, платежи, DSCR).
- `model_version` — `scorecard-1.0+products-1.0`.
- Неизвестный продукт → 422 `unknown_product`.
- Проверено: тесты ядра (30 шт.) проходят с `CORE_SCORING_MODE=http CORE_SCORING_URL=http://localhost:8001`. Демо: 7701234567 → APPROVE, 7702345678 при 10 млн → COUNTER_OFFER 6,6 млн на 36 мес., 7703456789 → MANUAL_REVIEW.
- В `docker-compose.yml` нужно добавить сервис `scoring` (`build: ./services/scoring`, healthcheck уже в Dockerfile) и `CORE_SCORING_MODE=http` — это за тобой, как договорились.
- Новых библиотек для THIRD_PARTY_NOTICES нет: FastAPI, Uvicorn, pydantic, pydantic-settings, PyYAML, pytest, HTTPX уже перечислены.

