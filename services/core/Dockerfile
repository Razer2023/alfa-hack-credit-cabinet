# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv

WORKDIR /app

# Сначала только зависимости — слой кешируется, пока не меняется uv.lock
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini docker-entrypoint.sh ./
COPY migrations ./migrations
COPY app ./app

RUN useradd --system --uid 10001 core && chmod +x docker-entrypoint.sh
USER core

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')"

ENTRYPOINT ["./docker-entrypoint.sh"]
