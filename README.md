# Умный кредитный кабинет предпринимателя

Прототип цифрового кредитного конвейера для малого и микробизнеса (Альфа Хак 2026): кабинет клиента и рабочее место банка в едином процессе, от выбора продукта до выдачи.

> Все четыре части собраны в одном `docker compose`: веб (D), ядро (A), интеграции (B), скоринг (C).

## Запуск

Нужен Docker Desktop (или Docker Engine с Compose v2).

```bash
cp .env.example .env
docker compose up --build
```

| Что | Адрес |
|---|---|
| Веб-интерфейс | http://localhost:3000 |
| Swagger ядра (A) | http://localhost:8080/docs |
| Swagger интеграций (B) | http://localhost:8081/docs |
| Swagger скоринга (C) | http://localhost:8082/docs |

- Демо-пользователи: `coffee`, `stroy`, `vector` (клиенты), `manager`, `underwriter`. Пароль — `CORE_DEMO_PASSWORD` из `.env`.
- Какая компания даёт какой исход — в [docs/architecture/core.md](docs/architecture/core.md#сервисы-b-и-c).
- Сквозная проверка всех трёх сценариев после запуска:
  ```bash
  cd services/core && uv run python ../../deploy/e2e/scenarios.py
  ```
  Её же на каждом PR выполняет CI (`core-e2e`): поднимает весь compose и проходит сценарии.

## Архитектура и контракты
- [Ядро: конвейер, безопасность, ограничения](docs/architecture/core.md)
- [Статусы заявки (диаграмма)](docs/architecture/statuses.md)
- [Модель данных](docs/architecture/data-model.md)
- [OpenAPI ядра](contracts/core.yaml)

## Разработка ядра без Docker
```bash
cd services/core
uv sync
uv run pytest
uv run alembic upgrade head && uv run python -m app.seed && uv run uvicorn app.main:app --reload
```
По умолчанию используется локальная SQLite (`core.db`). После изменения API или статусов: `uv run python -m app.export_docs`.

## Для команды
- [Правила работы](CONTRIBUTING.md)
- [Области ответственности](docs/team/AREAS.md)
- [Настройка GitHub и ежедневный цикл](docs/team/GITHUB_SETUP.md)
- [ТЗ между областями](tz/README.md)
- [Дизайн: Core Components Альфа-Банка](docs/design/DESIGN.md)
