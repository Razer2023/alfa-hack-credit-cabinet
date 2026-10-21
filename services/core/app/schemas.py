import uuid
from datetime import datetime
from typing import Literal

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


class ApplicationOut(BaseModel):
    id: uuid.UUID
    number: str
    status: StatusOut
    allowed_actions: list[str] = Field(description="Действия, доступные текущему пользователю: какие кнопки показать")
    product_code: str
    amount: int | None
    term_months: int | None
    purpose: str | None
    form: dict = Field(description="company — поля по ИНН с источником; extra — сведения, введённые клиентом")
    need_info: dict | None = Field(description="Что банк просит дополнить (в статусе NEED_INFO)")
    decision: dict | None
    offers: list[OfferOut]
    company: CompanyOut
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    status_changed_at: datetime


class ApplicationBankOut(ApplicationOut):
    enrichment: dict | None
    scoring: dict | None
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


class InfoItem(BaseModel):
    field: str
    message: str


class InfoRequestIn(BaseModel):
    items: list[InfoItem] = Field(min_length=1)
    comment: str | None = Field(None, max_length=1000)


class StatusReferenceOut(BaseModel):
    code: ApplicationStatus
    title: str
    hint: str
    terminal: bool
    next: list[ApplicationStatus]
