import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ApplicationStatus, OfferKind, OfferStatus, Role


class ErrorOut(BaseModel):
    code: str
    message: str


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inn: str
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    login: str
    full_name: str
    role: Role
    company: CompanyOut | None


class LoginIn(BaseModel):
    login: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProductOut(BaseModel):
    code: str
    name: str
    description: str
    min_amount: int
    max_amount: int
    min_term_months: int
    max_term_months: int
    base_rate: float


class PaymentCalcIn(BaseModel):
    product_code: str
    amount: int = Field(gt=0, le=1_000_000_000)
    term_months: int = Field(gt=0, le=120)


class PaymentCalcOut(BaseModel):
    rate: float
    monthly_payment: int
    total_payment: int
    overpayment: int


class StatusOut(BaseModel):
    code: ApplicationStatus
    title: str
    hint: str


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: OfferKind
    status: OfferStatus
    amount: int
    term_months: int
    rate: float
    monthly_payment: int
    created_at: datetime


# --- Данные внутри заявки -----------------------------------------------------------------
# Формат задают сервисы B и C и само ядро; схемы только описывают его для контракта.
# Open — можно получить больше полей, чем описано: неизвестные поля сохраняются в ответе.


class Open(BaseModel):
    model_config = ConfigDict(extra="allow")


class DataSource(StrEnum):
    EGRUL = "EGRUL"
    FNS = "FNS"
    BANK_ACCOUNT = "BANK_ACCOUNT"


class CompanyField(BaseModel):
    value: str | int | float | bool
    source: DataSource = Field(description="Откуда значение: ЕГРЮЛ, ФНС или выписка по счёту")


class ApplicationForm(BaseModel):
    company: dict[str, CompanyField] | None = Field(
        None,
        description="Поля компании по ИНН (сервис B): name, ogrn, registration_date, okved, address, director, "
        "employees, tax_regime, revenue_year, avg_monthly_turnover; набор может расширяться",
    )
    extra: dict[str, Any] = Field(default_factory=dict, description="Сведения, которые ввёл клиент")


class InfoItem(BaseModel):
    field: str
    message: str


class NeedInfo(BaseModel):
    items: list[InfoItem]
    comment: str | None = None
    requested_by: Role = Field(description="SYSTEM — автоматическая проверка, MANAGER или UNDERWRITER — сотрудник")


class Reason(BaseModel):
    code: str
    text: str = Field(description="Текст для клиента")


DecisionResult = Literal["APPROVE", "COUNTER_OFFER", "REJECT", "MANUAL_REVIEW"]


class Decision(BaseModel):
    result: DecisionResult
    decided_by: Literal["SYSTEM", "MANAGER", "UNDERWRITER"]
    reasons: list[Reason] = Field(default_factory=list)
    comment: str | None = None


class EgrulData(Open):
    status: str
    liquidation: bool


class FnsData(Open):
    tax_debt: int
    mass_address: bool


class BkiData(Open):
    max_overdue_days: int
    active_loans: int
    total_debt: int


class Enrichment(Open):
    """Данные внешних проверок от сервиса B."""

    egrul: EgrulData
    fns: FnsData
    bki: BkiData


class Factor(Open):
    code: str
    title: str
    impact: int = Field(description="Баллы фактора: плюс повышает оценку, минус снижает")
    value: str | None = Field(None, description="Значение фактора для андеррайтера, например «8,4 года»")


class ScoringOffer(Open):
    amount: int
    term_months: int
    rate: float


class ScoringMetrics(Open):
    limit: int | None = None
    monthly_free_cash_flow: int | None = None
    existing_debt_payment: int | None = None
    new_payment: int | None = None
    dscr: float | None = None
    min_dscr: float | None = None


class ScoringResult(Open):
    """Ответ сервиса C на заявку."""

    result: DecisionResult
    score: int
    risk_class: str
    model_version: str
    factors: list[Factor] = Field(default_factory=list)
    reasons: list[Reason] = Field(default_factory=list)
    offers: list[ScoringOffer] = Field(default_factory=list)
    metrics: ScoringMetrics | None = None


# --- Заявка -------------------------------------------------------------------------------


class ApplicationOut(BaseModel):
    id: uuid.UUID
    number: str
    status: StatusOut
    allowed_actions: list[str] = Field(description="Действия, доступные текущему пользователю: какие кнопки показать")
    product_code: str
    amount: int | None
    term_months: int | None
    purpose: str | None
    form: ApplicationForm
    need_info: NeedInfo | None = Field(description="Что банк просит дополнить (в статусе NEED_INFO)")
    decision: Decision | None
    offers: list[OfferOut]
    company: CompanyOut
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    status_changed_at: datetime


class ApplicationBankOut(ApplicationOut):
    enrichment: Enrichment | None
    scoring: ScoringResult | None
    assignee_id: uuid.UUID | None


class ApplicationCreate(BaseModel):
    product_code: str


class ApplicationPatch(BaseModel):
    amount: int | None = Field(None, gt=0, le=1_000_000_000)
    term_months: int | None = Field(None, gt=0, le=120)
    purpose: str | None = Field(None, max_length=500)
    extra: dict | None = None


class InfoProvideIn(ApplicationPatch):
    comment: str | None = Field(None, max_length=1000)


class PrefillIn(BaseModel):
    inn: str = Field(pattern=r"^\d{10}(\d{2})?$")


class CodeRequestOut(BaseModel):
    confirmation_id: uuid.UUID
    expires_at: datetime
    demo_code: str | None = Field(
        description="Код показывается в интерфейсе вместо SMS (демо-режим, CORE_DEMO_CODES=true)"
    )


class CodeConfirmIn(BaseModel):
    confirmation_id: uuid.UUID
    code: str = Field(pattern=r"^\d{6}$")


class CancelIn(BaseModel):
    reason: str | None = Field(None, max_length=500)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: uuid.UUID
    type: str
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus | None
    actor_role: Role
    message: str
    payload: dict
    created_at: datetime


class DecisionIn(BaseModel):
    result: Literal["APPROVE", "COUNTER_OFFER", "REJECT"]
    amount: int | None = Field(None, gt=0, le=1_000_000_000)
    term_months: int | None = Field(None, gt=0, le=120)
    rate: float | None = Field(None, gt=0, lt=100)
    comment: str | None = Field(None, max_length=1000)


class EscalateIn(BaseModel):
    comment: str | None = Field(None, max_length=1000)


class InfoRequestIn(BaseModel):
    items: list[InfoItem] = Field(min_length=1)
    comment: str | None = Field(None, max_length=1000)


class StatusReferenceOut(BaseModel):
    code: ApplicationStatus
    title: str
    hint: str
    terminal: bool
    next: list[ApplicationStatus]
