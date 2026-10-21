---
to: A-core
from: D
story: S3.1, S4.5, S5.3, S6.1, S6.3
priority: normal
status: new
done_in: ""
---

# Типы для полей form, need_info, decision, enrichment, scoring в contracts/core.yaml

## Зачем
По ТЗ [2026-10-21-a-core-api.md](../D-web/2026-10-21-a-core-api.md) веб генерирует типы из контракта (`openapi-typescript`), а не пишет их руками. Сейчас в `ApplicationOut` и `ApplicationBankOut` пять полей описаны как `type: object, additionalProperties: true`, и в TypeScript они превращаются в `Record<string, unknown>`. Экраны читают поля внутри них:

| Поле | Где нужно веб-интерфейсу | Story |
|---|---|---|
| `form.company.<поле>.value / source` | мастер заявки: значения по ИНН и бейдж «ЕГРЮЛ / ФНС / Выписка» | S3.1 |
| `need_info.items[].message`, `need_info.comment` | экран «Нужны данные» и форма дополнения | S4.5 |
| `decision.result`, `decision.reasons[].text` | экран решения, причина отказа | S6.1, S6.3 |
| `enrichment.egrul / fns / bki` | карточка андеррайтера | S5.3 |
| `scoring.score`, `risk_class`, `factors`, `reasons` | карточка андеррайтера | S5.3 |

## Что нужно сделать
Описать эти поля pydantic-схемами в `services/core/app/schemas.py` и перегенерировать контракт (`python -m app.export_docs`). Формат данных **не меняется**, это только описание того, что ядро уже отдаёт (`views.py`, `service.py`, `pipeline.py`, клиенты в `app/clients/`). Названия схем — на твоё усмотрение, ниже предложение.

1. **`form`** → `ApplicationForm`
   - `company`: `dict[str, CompanyField] | None` — ключи как в профиле B (`name`, `ogrn`, `registration_date`, `okved`, `address`, `director`, `employees`, `tax_regime`, `revenue_year`, `avg_monthly_turnover`; B может добавлять новые, поэтому словарь, а не фиксированный набор).
   - `CompanyField`: `value: str | int | float | bool`, `source: DataSource`, где `DataSource` — enum `EGRUL | FNS | BANK_ACCOUNT`.
   - `extra`: `dict[str, Any]` — сведения, которые ввёл клиент.
2. **`need_info`** → `NeedInfo | None`: `items: list[InfoItem]` (схема `InfoItem {field, message}` уже есть), `comment: str | None`, `requested_by: Role` (`SYSTEM`, `MANAGER` или `UNDERWRITER`).
3. **`decision`** → `Decision | None`: `result: APPROVE | COUNTER_OFFER | REJECT | MANUAL_REVIEW`, `decided_by: SYSTEM | UNDERWRITER`, `reasons: list[Reason]`, `comment: str | None`. `Reason`: `code: str`, `text: str`.
4. **`enrichment`** (только `ApplicationBankOut`) → `Enrichment | None`:
   - `egrul`: `status: str`, `liquidation: bool`;
   - `fns`: `tax_debt: int`, `mass_address: bool`;
   - `bki`: `max_overdue_days: int`, `active_loans: int`, `total_debt: int`.
   - Во всех трёх лучше оставить `additionalProperties: true`: B может прислать больше полей, веб покажет известные.
5. **`scoring`** (только `ApplicationBankOut`) → `ScoringResult | None`: `result`, `score: int`, `risk_class: str`, `model_version: str`, `factors: list[Factor]`, `reasons: list[Reason]`, `offers: list[{amount, term_months, rate}]`. `Factor`: `code: str`, `title: str`, `impact: int` — как в ТЗ [C-scoring](../C-scoring/2026-10-21-a-core-contract.md).

## Пример (если это API)
```http
GET /api/v1/bank/applications/{id}
```
```json
{
  "status": {"code": "MANUAL_REVIEW", "title": "У специалиста", "hint": "Заявку изучает кредитный специалист"},
  "form": {
    "company": {
      "name": {"value": "ООО «Вектор Трейд»", "source": "EGRUL"},
      "employees": {"value": 9, "source": "FNS"},
      "revenue_year": {"value": 18000000, "source": "BANK_ACCOUNT"}
    },
    "extra": {}
  },
  "need_info": null,
  "decision": {
    "result": "MANUAL_REVIEW",
    "decided_by": "SYSTEM",
    "reasons": [{"code": "BKI_OVERDUE", "text": "Просрочка 45 дн. в БКИ"}]
  },
  "enrichment": {
    "egrul": {"status": "ACTIVE", "liquidation": false},
    "fns": {"tax_debt": 0, "mass_address": false},
    "bki": {"max_overdue_days": 45, "active_loans": 3, "total_debt": 6000000}
  },
  "scoring": {
    "result": "MANUAL_REVIEW",
    "score": 480,
    "risk_class": "C",
    "model_version": "stub-1",
    "factors": [],
    "reasons": [{"code": "BKI_OVERDUE", "text": "Просрочка 45 дн. в БКИ"}],
    "offers": []
  }
}
```

## Готово, когда
- [ ] В `contracts/core.yaml` у `ApplicationOut` и `ApplicationBankOut` поля `form`, `need_info`, `decision`, `enrichment`, `scoring` ссылаются на схемы, а не на `type: object`
- [ ] Перечисления `source`, `decision.result`, `decided_by` — enum в контракте
- [ ] Ответы ядра не изменились: существующие тесты проходят, CI `core-test` зелёный (в том числе проверка актуальности контракта)
- [ ] `openapi-typescript` по новому контракту даёт типы с этими полями (можно проверить у меня в `web/`)

## Пока не сделано, я работаю так
Описываю эти типы вручную в `web/src/api/` по примерам выше и по коду ядра. Когда контракт обновится, удалю ручные типы и перейду на сгенерированные.

## Ответ владельца области
