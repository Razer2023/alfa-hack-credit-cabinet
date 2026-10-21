#!/bin/sh
set -e

echo "Миграции БД"
alembic upgrade head

if [ "${CORE_SEED:-true}" = "true" ]; then
    python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
