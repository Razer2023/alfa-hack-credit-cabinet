"""Каталог продуктов и расчёт платежа. Владелец логики — сервис C, ядро проксирует запросы для веба."""

from fastapi import APIRouter, Depends

from app import service
from app.clients import get_integrations, get_scoring
from app.clients.base import ExternalNotFound, ExternalRejected, ExternalServiceError
from app.deps import current_user, require
from app.errors import DomainError
from app.purposes import business_purposes
from app.models import Role, User
from app.schemas import (
    PaymentCalcIn,
    PaymentCalcOut,
    PrecheckIn,
    PrecheckOut,
    ProductMatchIn,
    ProductMatchOut,
    ProductOut,
    PurposesOut,
    StatusReferenceOut,
)
from app.statemachine import STATUS_INFO, TERMINAL, TRANSITIONS

router = APIRouter(tags=["Справочники"], dependencies=[Depends(current_user)])


@router.get("/products", response_model=list[ProductOut], summary="Кредитные продукты (S1.1)")
def products() -> list[dict]:
    return get_scoring().list_products()


@router.get("/products/purposes", response_model=PurposesOut, summary="Цели кредита под бизнес клиента (S1.2)")
def purposes(user: User = Depends(current_user)) -> dict:
    catalog = service.product_purposes(get_scoring().list_products())
    return business_purposes(catalog, _okved(user))


def _okved(user: User) -> str | None:
    # Отрасль — из профиля компании в ЕГРЮЛ (сервис B); недоступен — цели как в каталоге
    if user.company is None:
        return None
    try:
        fields = get_integrations().company_profile(user.company.inn)["fields"]
    except (ExternalServiceError, ExternalNotFound, ExternalRejected):
        return None
    return (fields.get("okved") or {}).get("value")


@router.post("/products/match", response_model=list[ProductMatchOut], summary="Подбор продукта по цели (S1.2)")
def match(body: ProductMatchIn) -> list[dict]:
    return service.match_products(get_scoring().list_products(), body.purpose, body.amount, body.term_months, body.title)


@router.post("/calc/payment", response_model=PaymentCalcOut, summary="Расчёт ежемесячного платежа (S3.2)")
def calc_payment(body: PaymentCalcIn) -> PaymentCalcOut:
    scoring = get_scoring()
    try:
        product = scoring.get_product(body.product_code)
    except ExternalNotFound:
        raise DomainError("unknown_product", "Такого кредитного продукта нет", 422) from None
    rate = product["base_rate"]
    return PaymentCalcOut(rate=rate, **scoring.calc_payment(body.amount, body.term_months, rate))


@router.get("/reference/statuses", response_model=list[StatusReferenceOut], summary="Статусы заявки и переходы")
def statuses() -> list[StatusReferenceOut]:
    return [
        StatusReferenceOut(
            code=status,
            title=info.title,
            hint=info.hint,
            sla=info.sla,
            terminal=status in TERMINAL,
            next=[dst for (src, dst) in TRANSITIONS if src == status],
        )
        for status, info in STATUS_INFO.items()
    ]


@router.post(
    "/precheck",
    response_model=PrecheckOut,
    summary="Предоценка суммы и шансов по ИНН (S2.1)",
    description=(
        "До подачи заявки: та же проверка данных компании (ЕГРЮЛ, ФНС, БКИ, выписка) и та же скоринговая "
        "логика, что у заявки, но без сохранения результата и без запроса в кредитную историю от имени заявки. "
        "Без суммы и срока — оценивает только максимум по продукту."
    ),
)
def precheck(body: PrecheckIn, user: User = Depends(require(Role.CLIENT))):
    return service.precheck(user, body.model_dump())
