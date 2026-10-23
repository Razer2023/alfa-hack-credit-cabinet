import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app import documents
from app.checks import check_application
from app.companies import company_profile, load_companies
from app.dashboard import load_dashboard
from app.documents import DocumentError
from app.enrichment import load_enrichment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_companies()
    load_enrichment()
    load_dashboard()
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


def _document_error(exc: DocumentError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"code": exc.code, "message": exc.message})


@app.get("/api/v1/dashboard/applications", tags=["Дашборд"], summary="Синтетические заявки для дашборда")
def dashboard_applications() -> list:
    return load_dashboard()


@app.post("/api/v1/document-requests", status_code=201, tags=["Документы"], summary="Запросить документы у клиента")
def create_document_request(body: dict):
    try:
        return documents.create_request(body)
    except DocumentError as exc:
        return _document_error(exc)


@app.get("/api/v1/document-requests", tags=["Документы"], summary="Запросы документов по заявке")
def document_requests(application_id: str | None = None) -> list:
    return documents.list_requests(application_id)


@app.get("/api/v1/document-requests/{request_id}", tags=["Документы"], summary="Один запрос документов")
def document_request(request_id: str):
    try:
        return documents.get_request(request_id)
    except DocumentError as exc:
        return _document_error(exc)


@app.post(
    "/api/v1/document-requests/{request_id}/items/{code}",
    tags=["Документы"],
    summary="Загрузить файл по пункту запроса",
)
async def upload_document(request_id: str, code: str, request: Request):
    try:
        return documents.save_file(
            request_id,
            code,
            request.headers.get("x-filename") or "document",
            request.headers.get("content-type") or "",
            await request.body(),
        )
    except DocumentError as exc:
        return _document_error(exc)


@app.get(
    "/api/v1/document-requests/{request_id}/items/{code}/file",
    tags=["Документы"],
    summary="Скачать загруженный файл",
)
def download_document(request_id: str, code: str):
    try:
        payload, content_type, filename = documents.read_file(request_id, code)
    except DocumentError as exc:
        return _document_error(exc)
    return Response(
        content=payload,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
