import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.checks import check_application
from app.companies import company_profile, load_companies
from app.enrichment import load_enrichment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_companies()
    load_enrichment()
    yield


app = FastAPI(
    title="Данные и интеграции",
    version="0.1.0",
    description="Моки ЕГРЮЛ, ФНС, БКИ и выписки по счёту. Профиль компании и проверка заявки. Область B.",
    lifespan=lifespan,
)


@app.get("/health", tags=["Служебное"], summary="Сервис жив")
def health() -> dict:
    return {"status": "ok"}


@app.get(
    "/api/v1/companies/{inn}/profile",
    tags=["Компании"],
    summary="Профиль компании по ИНН",
    responses={404: {"description": "Компания не найдена"}},
)
def profile(inn: str):
    found = company_profile(inn)
    if found is None:
        return JSONResponse(
            status_code=404,
            content={"code": "not_found", "message": "Компания не найдена"},
        )
    return found


@app.post(
    "/api/v1/checks",
    tags=["Проверки"],
    summary="Полнота заявки и данные ЕГРЮЛ, ФНС и БКИ",
)
def checks(body: dict):
    return check_application(body)
