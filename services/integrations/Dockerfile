FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" \
    INTEGRATIONS_COMPANIES_PATH=/app/data/synthetic/companies.json

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv

WORKDIR /app

COPY services/integrations/pyproject.toml services/integrations/uv.lock services/integrations/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY services/integrations/app ./app
COPY data/synthetic/companies.json ./data/synthetic/companies.json

RUN useradd --system --uid 10001 integrations
USER integrations

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
