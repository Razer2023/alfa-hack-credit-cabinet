---
to: A-core
from: C
story: S5.4
priority: normal
status: done
done_in: ""
---

# Проверять условия сотрудника через скоринг перед подтверждением

## Зачем
После #19 менеджер подтверждает рекомендацию и может поменять условия как угодно. Например, вернуть СтройМонтажу 10 млн на 12 месяцев, хотя скоринг посчитал, что платёж компании не по силам, и предложил 6,6 млн на 36. Сейчас это проходит без проверки, и на защите это легко заметить.

В скоринге появился эндпоинт `POST /api/v1/offers/check` (PR `feat/c-s5.4-offer-check`). Он проверяет условия по тем же правилам, что и автоматическое решение: рамки продукта, минимальная ставка, лимит по выручке, DSCR. Если сумма не проходит, подсказывает, сколько можно дать на этот срок. Нужно, чтобы ядро его вызывало.

## Что нужно сделать
1. **Клиент скоринга.** `check_offer(request)` в `ScoringClient`: HTTP — `POST /api/v1/offers/check`, заглушка — всегда `{"allowed": true, "checks": [], ...}`.
2. **`decide_manual`, перед `add_offer`** (для `APPROVE` и `COUNTER_OFFER`): отправить `snapshot(app) | {"enrichment": app.enrichment, "terms": terms}`.
   - `allowed: false` и действует **менеджер** → 422, код `offer_not_allowed`, в тексте — `checks[].text`. Подтвердить нельзя, только поменять условия или передать андеррайтеру.
   - `allowed: false` и действует **андеррайтер** → можно, но только с комментарием (обоснование отступления от политики, как в банке). Без комментария — 422 `override_comment_required`.
   - Результат проверки сохранить в `decision` (например, `decision.checks` и `decision.override: true`), чтобы в истории было видно, что условия выданы с отступлением.
3. **Эндпоинт для формы:** `POST /bank/applications/{id}/offer-check {amount, term_months, rate?}` → ответ скоринга как есть. Веб будет показывать предупреждения, пока сотрудник вводит условия, ещё до нажатия кнопки.
4. Если скоринг недоступен — не блокировать решение, а вернуть предупреждение (как `NO_FINANCIAL_DATA`). Тогда демо не упадёт из-за проверки.

## Пример (если это API)
```http
POST http://scoring:8000/api/v1/offers/check
```
```json
{
  "application_id": "…", "inn": "7702345678",
  "application": {"product_code": "WORKING_CAPITAL", "amount": 10000000, "term_months": 12, "purpose": "…"},
  "company": {"revenue_year": 30000000, "avg_monthly_turnover": 2500000, "registration_date": "2018-06-01", "employees": 35},
  "extra": {},
  "enrichment": {"egrul": {…}, "fns": {…}, "bki": {…}},
  "terms": {"amount": 10000000, "term_months": 12, "rate": null}
}
```
```json
{
  "allowed": false,
  "terms": {"amount": 10000000, "term_months": 12, "rate": 18.9},
  "monthly_payment": 921089,
  "checks": [{"code": "DSCR_TOO_LOW", "level": "error", "text": "Компания не потянет платёж: DSCR 0,46 при минимуме 1,25"}],
  "suggestion": {"amount": 2600000, "term_months": 12, "rate": 18.9},
  "score": 740, "risk_class": "A", "model_version": "scorecard-1.1+products-1.0",
  "metrics": {"limit": 10500000, "monthly_free_cash_flow": 500000, "existing_debt_payment": 157500,
              "new_payment": 921089, "dscr": 0.46, "min_dscr": 1.25}
}
```
`level: "warning"` подтверждению не мешает. `rate: null` — скоринг подставит ставку по классу риска.

## Готово, когда
- [ ] Менеджер не может подтвердить СтройМонтажу 10 млн на 12 мес., видит причину и подсказку 2,6 млн
- [ ] Андеррайтер может, но только с комментарием, и это видно в истории заявки
- [ ] Рекомендация скоринга без изменений подтверждается как раньше (она всегда проходит проверку, это покрыто тестом в скоринге)
- [ ] `POST /bank/applications/{id}/offer-check` есть в `contracts/core.yaml`

## Пока не сделано, я работаю так
Эндпоинт скоринга можно проверить в Swagger: `http://localhost:8082/docs` → `POST /api/v1/offers/check`.

## Ответ владельца области
Принято и сделано.

- `check_offer` в клиенте скоринга (HTTP и заглушка). Вызов — в `decide_manual` перед созданием условий, запрос: `snapshot(app) | {"enrichment", "terms"}`.
- `allowed: false`: менеджер → 422 `offer_not_allowed`, в тексте `checks[].text` и подсказка «Допустимо до N ₽ на M мес.»; андеррайтер без комментария → 422 `override_comment_required`, с комментарием — можно.
- В решении сохраняются `decision.checks` и `decision.override`. При отступлении в истории банка появляется событие `POLICY_OVERRIDE` с обоснованием, клиенту оно не показывается.
- Эндпоинт для формы: `POST /bank/applications/{id}/offer-check {amount, term_months, rate?}` → ответ скоринга (схема `OfferCheckOut` в `contracts/core.yaml`). Заявку не меняет. До проверок (нет `enrichment`) → 409.
- Скоринг недоступен → решение не блокируется, в `checks` предупреждение `CHECK_UNAVAILABLE`.
- Проверено на живом скоринге (`scorecard-1.1`): менеджер не может подтвердить СтройМонтажу 10 млн / 12 мес. (DSCR 0,46, допустимо до 2 600 000 ₽); андеррайтер — только с комментарием, это видно в истории. Рекомендация без изменений подтверждается как раньше. Сценарий добавлен в `deploy/e2e/scenarios.py`.

Для веба (ТЗ `tz/D-web/2026-10-23-c-offer-check.md`) эндпоинт готов, типы в `web/src/api/schema.d.ts` перегенерированы.
