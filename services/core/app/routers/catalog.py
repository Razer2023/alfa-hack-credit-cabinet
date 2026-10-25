"""Каталог продуктов и расчёт платежа. Владелец логики — сервис C, ядро проксирует запросы для веба."""

from fastapi import APIRouter, Depends

from app.clients import get_scoring
from app.clients.base import ExternalNotFound
from app.deps import current_user
from app.errors import DomainError
from app.schemas import PaymentCalcIn, PaymentCalcOut, ProductOut, StatusReferenceOut
from app.statemachine import STATUS_INFO, TERMINAL, TRANSITIONS

router = APIRouter(tags=["Справочники"], dependencies=[Depends(current_user)])


@router.get("/products", response_model=list[ProductOut], summary="Кредитные продукты (S1.1)")
def products() -> list[dict]:
    return get_scoring().list_products()


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
