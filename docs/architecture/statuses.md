# Статусы заявки

> Файл сгенерирован из `services/core/app/statemachine.py` командой `python -m app.export_docs`. Руками не править.

На стрелках — кто выполняет переход: `CLIENT` — клиент, `SYSTEM` — автоматический конвейер, `MANAGER` / `UNDERWRITER` — сотрудники банка.

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> SUBMITTED: CLIENT
    DRAFT --> CANCELLED: CLIENT
    SUBMITTED --> CHECKING: SYSTEM
    CHECKING --> NEED_INFO: SYSTEM
    CHECKING --> SCORING: SYSTEM
    NEED_INFO --> CHECKING: CLIENT
    NEED_INFO --> CANCELLED: CLIENT
    SCORING --> APPROVED: SYSTEM
    SCORING --> COUNTER_OFFER: SYSTEM
    SCORING --> REJECTED: SYSTEM
    SCORING --> MANUAL_REVIEW: SYSTEM
    MANUAL_REVIEW --> APPROVED: UNDERWRITER
    MANUAL_REVIEW --> COUNTER_OFFER: UNDERWRITER
    MANUAL_REVIEW --> REJECTED: UNDERWRITER
    MANUAL_REVIEW --> NEED_INFO: MANAGER, UNDERWRITER
    COUNTER_OFFER --> APPROVED: CLIENT
    COUNTER_OFFER --> CANCELLED: CLIENT
    APPROVED --> SIGNED: CLIENT
    APPROVED --> CANCELLED: CLIENT
    SIGNED --> ISSUED: SYSTEM
    CANCELLED --> [*]
    ISSUED --> [*]
    REJECTED --> [*]
```

| Код | Название | Что видит клиент | Финальный |
|---|---|---|---|
| `DRAFT` | Черновик | Заполните заявку и отправьте её на рассмотрение |  |
| `SUBMITTED` | Отправлена | Заявка принята, скоро начнём проверку |  |
| `CHECKING` | Проверка данных | Проверяем данные компании в ЕГРЮЛ, ФНС и бюро кредитных историй |  |
| `NEED_INFO` | Нужны данные | Банку не хватает информации — дополните заявку |  |
| `SCORING` | Оценка | Оцениваем заявку и подбираем условия |  |
| `MANUAL_REVIEW` | У специалиста | Заявку изучает кредитный специалист |  |
| `APPROVED` | Одобрена | Проверьте условия и подпишите договор |  |
| `COUNTER_OFFER` | Другие условия | Банк готов выдать кредит на других условиях — посмотрите предложение |  |
| `REJECTED` | Отказ | Банк не может одобрить заявку сейчас | да |
| `SIGNED` | Подписана | Договор подписан, перечисляем деньги |  |
| `ISSUED` | Деньги зачислены | Кредит выдан, деньги на расчётном счёте | да |
| `CANCELLED` | Отменена | Заявка отменена | да |
