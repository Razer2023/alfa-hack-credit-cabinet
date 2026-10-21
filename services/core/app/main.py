import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm.exc import StaleDataError

from app.clients.base import ExternalServiceError
from app.config import settings
from app.db import engine
from app.errors import DomainError
from app.pipeline import Worker
from app.routers import auth, bank, catalog, client, stream
from app.schemas import ErrorOut

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    worker = Worker(settings.worker_poll_seconds, settings.pipeline_step_delay_seconds)
    if settings.worker_enabled:
        worker.start()
    yield
    worker.stop()


app = FastAPI(
    title="Ядро кредитного конвейера",
    version="0.1.0",
    description="Заявки, статусы, журнал событий, роли, подписание и выдача. Область A.",
    lifespan=lifespan,
    responses={
        401: {"model": ErrorOut, "description": "Нужно войти"},
        403: {"model": ErrorOut, "description": "Недостаточно прав"},
        409: {"model": ErrorOut, "description": "Действие недоступно в текущем статусе"},
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


@app.exception_handler(DomainError)
async def domain_error(_: Request, exc: DomainError):
    return _error(exc.http_status, exc.code, exc.message)


@app.exception_handler(ExternalServiceError)
async def external_error(_: Request, exc: ExternalServiceError):
    logging.getLogger(__name__).warning("Внешний сервис: %s", exc)
    return _error(503, "service_unavailable", "Сервис временно недоступен, попробуйте чуть позже")


@app.exception_handler(StaleDataError)
async def stale_error(_: Request, __: StaleDataError):
    return _error(409, "conflict", "Заявка изменилась, обновите страницу")


for router in (auth.router, catalog.router, client.router, bank.router, stream.router):
    app.include_router(router, prefix=API_PREFIX)


@app.get("/health/live", tags=["Служебное"], summary="Процесс жив")
def live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready", tags=["Служебное"], summary="Готов принимать запросы (БД доступна)")
def ready() -> dict:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
