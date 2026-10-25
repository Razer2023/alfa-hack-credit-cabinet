import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow


class Role(StrEnum):
    CLIENT = "CLIENT"
    MANAGER = "MANAGER"
    UNDERWRITER = "UNDERWRITER"
    SYSTEM = "SYSTEM"


class ApplicationStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    CHECKING = "CHECKING"
    NEED_INFO = "NEED_INFO"
    SCORING = "SCORING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    APPROVED = "APPROVED"
    COUNTER_OFFER = "COUNTER_OFFER"
    REJECTED = "REJECTED"
    SIGNED = "SIGNED"
    ISSUED = "ISSUED"
    CANCELLED = "CANCELLED"


class OfferKind(StrEnum):
    STANDARD = "STANDARD"
    COUNTER = "COUNTER"


class OfferStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class ConfirmationPurpose(StrEnum):
    SUBMIT = "SUBMIT"
    SIGN = "SIGN"


def _enum(enum_cls: type[StrEnum]) -> Enum:
    return Enum(enum_cls, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e])


# В SQLite автоинкремент работает только у INTEGER PRIMARY KEY
EventId = BigInteger().with_variant(Integer, "sqlite")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inn: Mapped[str] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    login: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role))
    company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id"))
    # Контакты сотрудника банка: клиент видит, кто ведёт заявку и как связаться (S4.9)
    position: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    work_hours: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped[Company | None] = relationship()


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    number: Mapped[str] = mapped_column(String(20), unique=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    # Персональный менеджер: назначается при отправке, клиент видит его контакты (S4.9)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    product_code: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int | None] = mapped_column(BigInteger)  # рубли
    term_months: Mapped[int | None] = mapped_column(Integer)
    purpose: Mapped[str | None] = mapped_column(String(500))
    # Анкета: поля компании с источником (ЕГРЮЛ, ФНС, выписка, клиент) и дополнительные сведения
    form: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[ApplicationStatus] = mapped_column(_enum(ApplicationStatus), index=True)
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    # Когда фоновому обработчику можно повторить шаг после сбоя внешнего сервиса
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    need_info: Mapped[dict | None] = mapped_column(JSON)  # что банк просит дополнить
    enrichment: Mapped[dict | None] = mapped_column(JSON)  # данные внешних проверок (сервис B)
    scoring: Mapped[dict | None] = mapped_column(JSON)  # результат скоринга (сервис C)
    decision: Mapped[dict | None] = mapped_column(JSON)  # итоговое решение и причины

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)

    company: Mapped[Company] = relationship()
    manager: Mapped[User | None] = relationship(foreign_keys=[manager_id])
    offers: Mapped[list["Offer"]] = relationship(back_populates="application", order_by="Offer.created_at")

    __mapper_args__ = {"version_id_col": version}


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    kind: Mapped[OfferKind] = mapped_column(_enum(OfferKind))
    status: Mapped[OfferStatus] = mapped_column(_enum(OfferStatus), default=OfferStatus.PROPOSED)
    amount: Mapped[int] = mapped_column(BigInteger)
    term_months: Mapped[int] = mapped_column(Integer)
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    monthly_payment: Mapped[int] = mapped_column(BigInteger)
    created_by_role: Mapped[Role] = mapped_column(_enum(Role))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    application: Mapped[Application] = relationship(back_populates="offers")


class ApplicationEvent(Base):
    """Журнал событий заявки. Из него строятся трекер, уведомления, аудит и аналитика этапов."""

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(EventId, primary_key=True, autoincrement=True)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    from_status: Mapped[ApplicationStatus | None] = mapped_column(_enum(ApplicationStatus))
    to_status: Mapped[ApplicationStatus | None] = mapped_column(_enum(ApplicationStatus))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[Role] = mapped_column(_enum(Role))
    message: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    visible_to_client: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Confirmation(Base):
    """Одноразовый код подтверждения (мок простой электронной подписи)."""

    __tablename__ = "confirmations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    purpose: Mapped[ConfirmationPurpose] = mapped_column(_enum(ConfirmationPurpose))
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Message(Base):
    """Переписка клиента и банка внутри заявки (S4.10). Всё общение — в кабинете, без почты и мессенджеров."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(EventId, primary_key=True, autoincrement=True)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    author_role: Mapped[Role] = mapped_column(_enum(Role))
    text: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    author: Mapped[User] = relationship()
