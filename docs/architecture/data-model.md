# Модель данных ядра

Схема БД ядра (PostgreSQL). Источник правды — `services/core/app/models.py`, миграции — `services/core/migrations/`.

```mermaid
erDiagram
    companies ||--o{ users : "сотрудники клиента"
    companies ||--o{ applications : "подаёт"
    users ||--o{ applications : "создаёт / ведёт"
    applications ||--o{ offers : "условия"
    applications ||--o{ application_events : "журнал"
    applications ||--o{ confirmations : "коды подтверждения"

    companies {
        uuid id PK
        string inn UK "ИНН"
        string name
    }
    users {
        uuid id PK
        string login UK
        string password_hash "PBKDF2-SHA256"
        enum role "CLIENT | MANAGER | UNDERWRITER"
        uuid company_id FK "только у клиентов"
    }
    applications {
        uuid id PK
        string number UK "K-XXXXXXXX"
        uuid company_id FK
        string product_code "код продукта сервиса C"
        bigint amount "рубли"
        int term_months
        string purpose
        json form "company: поля по ИНН с источником; extra: от клиента"
        enum status "см. statuses.md"
        timestamp status_changed_at
        timestamp retry_at "повтор шага после сбоя"
        json need_info "что дополнить"
        json enrichment "ЕГРЮЛ, ФНС, БКИ (сервис B)"
        json scoring "скоринг (сервис C)"
        json decision "итог и причины"
        uuid assignee_id FK "сотрудник банка"
        int version "оптимистичная блокировка"
    }
    offers {
        uuid id PK
        uuid application_id FK
        enum kind "STANDARD | COUNTER"
        enum status "PROPOSED | ACCEPTED | DECLINED"
        bigint amount
        int term_months
        numeric rate
        bigint monthly_payment
        enum created_by_role "SYSTEM | UNDERWRITER"
    }
    application_events {
        bigint id PK "курсор для SSE"
        uuid application_id FK
        uuid company_id FK "фильтр для клиента"
        string type "CREATED | PREFILLED | STATUS_CHANGED | ASSIGNED | DELAYED"
        enum from_status
        enum to_status
        enum actor_role
        string message "текст для трекера"
        json payload
        bool visible_to_client
    }
    confirmations {
        uuid id PK
        uuid application_id FK
        enum purpose "SUBMIT | SIGN"
        string code_hash "HMAC, сам код не хранится"
        int attempts "не больше 5"
        timestamp expires_at
        timestamp used_at
    }
```

## Почему так

- **Журнал событий отдельной таблицей.** Каждое изменение статуса пишется туда же, где меняется заявка, в одной транзакции. Из журнала строятся трекер клиента, SSE-уведомления, аудит («кто и когда принял решение») и статистика длительности этапов (S4.6, S8.1).
- **JSON для данных внешних сервисов.** Формат ответов B и C ещё меняется. Ядро хранит их как есть и не зависит от их внутренней структуры.
- **Деньги — целые рубли (`bigint`), ставка — `numeric(5,2)`.** Никаких float в суммах.
- **`version` — оптимистичная блокировка.** Если заявку одновременно меняют двое, второй получит 409 «Заявка изменилась, обновите страницу».
