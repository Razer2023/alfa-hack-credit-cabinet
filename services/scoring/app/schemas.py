"""Схемы API сервиса. Из них генерируется contracts/scoring.yaml (python -m app.export_docs)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DecisionResult = Literal["APPROVE", "COUNTER_OFFER", "REJECT", "MANUAL_REVIEW"]


class Open(BaseModel):
    """Входные данные от ядра и сервиса B: лишние поля допустимы, известные — проверяются."""

    model_config = ConfigDict(extra="allow")


# --- Каталог и расчёты ---


class ProductOut(BaseModel):
    code: str = Field(examples=["EXPRESS"])
    name: str = Field(examples=["Экспресс-кредит"])
    description: str
    min_amount: int = Field(examples=[300000])
    max_amount: int = Field(examples=[5000000])
    min_term_months: int = Field(examples=[3])
    max_term_months: int = Field(examples=[24])
    base_rate: float = Field(description="Базовая ставка, % годовых", examples=[22.5])
    purposes: list[str] = Field(description="Типичные цели кредита (для подбора продукта)")


class PaymentIn(BaseModel):
    amount: int = Field(gt=0, le=1_000_000_000, examples=[1200000])
    term_months: int = Field(gt=0, le=120, examples=[12])
    rate: float = Field(ge=0, lt=100, description="% годовых", examples=[22.5])


class PaymentOut(BaseModel):
    monthly_payment: int = Field(description="Аннуитетный платёж, ₽", examples=[112602])
    total_payment: int = Field(examples=[1351224])
    overpayment: int = Field(examples=[151224])


# --- Кредитное решение ---


class ApplicationIn(Open):
    product_code: str = Field(examples=["WORKING_CAPITAL"])
    amount: int = Field(gt=0, examples=[10000000])
    term_months: int = Field(gt=0, examples=[12])
    purpose: str | None = None


class CompanyIn(Open):
    """Значения полей анкеты компании (из профиля сервиса B). Все поля необязательны."""

    revenue_year: float | None = Field(None, examples=[30000000])
    avg_monthly_turnover: float | None = Field(None, examples=[2500000])
    registration_date: date | None = Field(None, examples=["2018-06-01"])
    employees: int | None = Field(None, examples=[35])


class EgrulIn(Open):
    status: str = "ACTIVE"
    liquidation: bool = False


class FnsIn(Open):
    tax_debt: float = 0
    mass_address: bool = False


class BkiIn(Open):
    max_overdue_days: int = Field(0, ge=0)
    active_loans: int = Field(0, ge=0)
    total_debt: float = Field(0, ge=0)


class EnrichmentIn(Open):
    egrul: EgrulIn = EgrulIn()
    fns: FnsIn = FnsIn()
    bki: BkiIn | None = None


class DecisionIn(Open):
    application_id: str | None = None
    inn: str | None = Field(None, examples=["7702345678"])
    application: ApplicationIn
    company: CompanyIn = CompanyIn()
    extra: dict = {}
    enrichment: EnrichmentIn = EnrichmentIn()


class FactorOut(BaseModel):
    code: str = Field(examples=["BUSINESS_AGE"])
    title: str = Field(examples=["Возраст бизнеса"])
    impact: int = Field(description="Баллы фактора: плюс повышает оценку, минус снижает", examples=[60])
    value: str = Field(description="Значение фактора для андеррайтера", examples=["8,4 года"])


class ReasonOut(BaseModel):
    code: str = Field(examples=["AMOUNT_OVER_LIMIT"])
    text: str = Field(description="Текст для клиента, человеческим языком")


class OfferOut(BaseModel):
    amount: int = Field(examples=[6500000])
    term_months: int = Field(examples=[36])
    rate: float = Field(examples=[18.9])


class MetricsOut(BaseModel):
    """Расчёт платёжеспособности для карточки андеррайтера."""

    limit: int | None = Field(None, description="Лимит по выручке для класса риска, ₽")
    monthly_free_cash_flow: int | None = None
    existing_debt_payment: int | None = Field(None, description="Оценка платежа по текущим кредитам, ₽/мес")
    new_payment: int | None = Field(None, description="Платёж по запрошенным условиям, ₽/мес")
    dscr: float | None = Field(None, description="Покрытие платежей свободным денежным потоком")
    min_dscr: float


class DecisionOut(BaseModel):
    result: DecisionResult
    score: int = Field(examples=[740])
    risk_class: str = Field(examples=["A"])
    model_version: str = Field(examples=["scorecard-1.1+products-1.0"])
    factors: list[FactorOut]
    reasons: list[ReasonOut]
    offers: list[OfferOut] = Field(description="APPROVE — одно, COUNTER_OFFER — одно или несколько, иначе пусто")
    metrics: MetricsOut


# --- Проверка условий сотрудника банка (S5.4) ---


class TermsIn(BaseModel):
    amount: int = Field(gt=0, le=1_000_000_000, examples=[10000000])
    term_months: int = Field(gt=0, le=120, examples=[12])
    rate: float | None = Field(
        None, gt=0, lt=100, description="% годовых; не указана — ставка по классу риска", examples=[18.9]
    )


class OfferCheckIn(DecisionIn):
    """Та же заявка, что для /decisions, плюс условия, которые вписал сотрудник."""

    terms: TermsIn


class CheckOut(BaseModel):
    code: str = Field(examples=["DSCR_TOO_LOW"])
    level: Literal["error", "warning"] = Field(
        description="error — условия не проходят политику банка, warning — проверить не удалось"
    )
    text: str = Field(description="Текст для сотрудника банка")


class SuggestionOut(BaseModel):
    amount: int = Field(description="Максимальная допустимая сумма на этот срок и ставку", examples=[2600000])
    term_months: int
    rate: float


class OfferCheckOut(BaseModel):
    allowed: bool = Field(description="Нет ни одной ошибки (warning не мешает)")
    terms: OfferOut = Field(description="Проверенные условия; ставка подставлена, если не была указана")
    monthly_payment: int
    checks: list[CheckOut]
    suggestion: SuggestionOut | None = Field(
        None, description="Если сумма не проходит — сколько можно дать на этот срок. Null, если сумма проходит или посчитать нельзя"
    )
    score: int
    risk_class: str
    model_version: str
    metrics: MetricsOut


class HealthOut(BaseModel):
    status: Literal["ok"]
    model_version: str


class ErrorOut(BaseModel):
    code: str
    message: str
