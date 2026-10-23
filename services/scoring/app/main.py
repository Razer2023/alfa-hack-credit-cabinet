import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.calc import payment_schedule
from app.engine import UnknownProduct, check_offer, decide
from app.rules import get_rules
from app.schemas import (
    DecisionIn,
    DecisionOut,
    ErrorOut,
    HealthOut,
    OfferCheckIn,
    OfferCheckOut,
    PaymentIn,
    PaymentOut,
    ProductOut,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("scoring")
API_PREFIX = "/api/v1"

# Правила проверяются при импорте: сервис с битым конфигом не стартует
get_rules()

app = FastAPI(
    title="Скоринг и кредитное решение",
    version="0.1.0",
    description=(
        "Каталог продуктов, расчёт платежа, балльная карта и кредитная логика. Область C. "
        "Правила — в services/scoring/rules/*.yaml, их версия возвращается в model_version."
    ),
)


@app.exception_handler(UnknownProduct)
async def unknown_product(_: Request, exc: UnknownProduct):
    return JSONResponse(status_code=422, content={"code": "unknown_product", "message": f"Нет продукта {exc}"})


@app.get("/health", response_model=HealthOut, tags=["service"])
def health():
    return {"status": "ok", "model_version": get_rules().model_version}


@app.get(f"{API_PREFIX}/products", response_model=list[ProductOut], tags=["products"], summary="Каталог продуктов (S1.1)")
def list_products():
    return [p.model_dump() for p in get_rules().catalog.products]


@app.get(
    f"{API_PREFIX}/products/{{code}}",
    response_model=ProductOut,
    responses={404: {"model": ErrorOut}},
    tags=["products"],
    summary="Продукт по коду (S1.1)",
)
def get_product(code: str):
    product = get_rules().catalog.get(code)
    if product is None:
        return JSONResponse(status_code=404, content={"code": "not_found", "message": f"Нет продукта {code}"})
    return product.model_dump()


@app.post(f"{API_PREFIX}/calc/payment", response_model=PaymentOut, tags=["calc"], summary="Аннуитетный платёж (S3.2)")
def calc_payment(body: PaymentIn):
    return payment_schedule(body.amount, body.term_months, body.rate)


@app.post(
    f"{API_PREFIX}/decisions",
    response_model=DecisionOut,
    responses={422: {"model": ErrorOut, "description": "Неизвестный продукт или некорректная заявка"}},
    tags=["decisions"],
    summary="Кредитное решение (S5.1, S5.2, S6.1)",
)
def make_decision(body: DecisionIn):
    out = decide(body, get_rules())
    log.info(
        "Заявка %s ИНН %s: %s, балл %s, класс %s",
        body.application_id, body.inn, out["result"], out["score"], out["risk_class"],
    )
    return out


@app.post(
    f"{API_PREFIX}/offers/check",
    response_model=OfferCheckOut,
    responses={422: {"model": ErrorOut, "description": "Неизвестный продукт или некорректная заявка"}},
    tags=["decisions"],
    summary="Проверка условий, которые вписал сотрудник банка (S5.4)",
)
def offer_check(body: OfferCheckIn):
    out = check_offer(body, get_rules())
    log.info(
        "Заявка %s: проверка условий %s ₽ / %s мес. — %s",
        body.application_id, body.terms.amount, body.terms.term_months, "ок" if out["allowed"] else "не проходят",
    )
    return out
