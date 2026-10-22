"""Операции с заявкой. Каждая меняет статус только через transition(), чтобы все переходы попадали в журнал."""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.clients import get_integrations, get_scoring
from app.clients.base import ExternalNotFound
from app.config import settings
from app.db import as_utc, utcnow
from app.errors import DomainError
from app.models import (
    Application,
    ApplicationEvent,
    ApplicationStatus as S,
    Confirmation,
    ConfirmationPurpose,
    Offer,
    OfferKind,
    OfferStatus,
    Role,
    User,
)
from app.security import hash_code, new_code
from app.statemachine import STATUS_INFO, TERMINAL, allowed_roles

EDITABLE = (S.DRAFT, S.NEED_INFO)
REQUIRED_FOR_SUBMIT = {"amount": "сумму", "term_months": "срок", "purpose": "цель"}


@dataclass(frozen=True)
class Actor:
    role: Role
    user_id: uuid.UUID | None = None

    @classmethod
    def of(cls, user: User) -> "Actor":
        return cls(user.role, user.id)


SYSTEM = Actor(Role.SYSTEM)


def record_event(
    session: Session,
    app: Application,
    actor: Actor,
    type_: str,
    message: str,
    *,
    payload: dict | None = None,
    visible: bool = True,
    from_status: S | None = None,
    to_status: S | None = None,
) -> ApplicationEvent:
    event = ApplicationEvent(
        application_id=app.id,
        company_id=app.company_id,
        type=type_,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor.user_id,
        actor_role=actor.role,
        message=message,
        payload=payload or {},
        visible_to_client=visible,
    )
    session.add(event)
    return event


def transition(
    session: Session,
    app: Application,
    to: S,
    actor: Actor,
    message: str | None = None,
    payload: dict | None = None,
) -> ApplicationEvent:
    roles = allowed_roles(app.status, to)
    if roles is None:
        raise DomainError("invalid_transition", f"Действие недоступно в статусе «{STATUS_INFO[app.status].title}»")
    if actor.role not in roles:
        raise DomainError("forbidden", "Недостаточно прав для этого действия", 403)
    source = app.status
    app.status = to
    app.status_changed_at = utcnow()
    app.retry_at = None
    app.retry_count = 0
    return record_event(
        session,
        app,
        actor,
        "STATUS_CHANGED",
        message or STATUS_INFO[to].title,
        payload=payload,
        from_status=source,
        to_status=to,
    )


def _require_status(app: Application, *statuses: S) -> None:
    if app.status not in statuses:
        raise DomainError("invalid_status", f"Действие недоступно в статусе «{STATUS_INFO[app.status].title}»")


def _apply_fields(app: Application, data: dict) -> None:
    for field in ("amount", "term_months", "purpose"):
        if data.get(field) is not None:
            setattr(app, field, data[field])
    if data.get("extra"):
        app.form = {**app.form, "extra": {**app.form.get("extra", {}), **data["extra"]}}


# --- клиент -------------------------------------------------------------------------------


def create_draft(session: Session, user: User, product_code: str) -> Application:
    try:
        get_scoring().get_product(product_code)
    except ExternalNotFound:
        raise DomainError("unknown_product", "Такого кредитного продукта нет", 422) from None
    app = Application(
        number=f"K-{uuid.uuid4().hex[:8].upper()}",
        company_id=user.company_id,
        created_by=user.id,
        product_code=product_code,
        status=S.DRAFT,
        form={},
    )
    session.add(app)
    session.flush()
    record_event(session, app, Actor.of(user), "CREATED", "Черновик заявки создан", to_status=S.DRAFT)
    return app


def update_draft(app: Application, data: dict) -> None:
    _require_status(app, S.DRAFT)
    _apply_fields(app, data)


def prefill(session: Session, app: Application, actor: Actor, inn: str) -> None:
    _require_status(app, *EDITABLE)
    if inn != app.company.inn:
        raise DomainError("inn_mismatch", "ИНН не совпадает с компанией вашего профиля", 422)
    try:
        profile = get_integrations().company_profile(inn)
    except ExternalNotFound:
        raise DomainError("company_not_found", "Компания с таким ИНН не найдена", 404) from None
    app.form = {**app.form, "company": profile["fields"]}
    record_event(session, app, actor, "PREFILLED", "Анкета заполнена по ИНН: ЕГРЮЛ, ФНС, выписка по счёту")


def request_code(session: Session, app: Application, user: User, purpose: ConfirmationPurpose) -> tuple[Confirmation, str]:
    if purpose == ConfirmationPurpose.SUBMIT:
        _require_status(app, S.DRAFT)
        missing = [title for field, title in REQUIRED_FOR_SUBMIT.items() if not getattr(app, field)]
        if missing:
            raise DomainError("incomplete", f"Укажите {', '.join(missing)} кредита", 422)
    else:
        _require_status(app, S.APPROVED)
        if active_offer(app) is None:
            raise DomainError("no_offer", "Нет условий для подписания", 409)

    code = new_code()
    confirmation = Confirmation(
        id=uuid.uuid4(),
        application_id=app.id,
        user_id=user.id,
        purpose=purpose,
        expires_at=utcnow() + timedelta(seconds=settings.code_ttl_seconds),
    )
    confirmation.code_hash = hash_code(confirmation.id, code)
    session.add(confirmation)
    return confirmation, code


def confirm_code(
    session: Session,
    app: Application,
    user: User,
    purpose: ConfirmationPurpose,
    confirmation_id: uuid.UUID,
    code: str,
) -> None:
    confirmation = session.get(Confirmation, confirmation_id)
    if (
        confirmation is None
        or confirmation.application_id != app.id
        or confirmation.user_id != user.id
        or confirmation.purpose != purpose
    ):
        raise DomainError("code_not_found", "Запросите код ещё раз", 404)
    if confirmation.used_at is not None:
        raise DomainError("code_used", "Код уже использован, запросите новый", 409)
    if as_utc(confirmation.expires_at) < utcnow():
        raise DomainError("code_expired", "Срок действия кода истёк, запросите новый", 409)
    if confirmation.attempts >= settings.code_max_attempts:
        raise DomainError("too_many_attempts", "Слишком много попыток, запросите новый код", 429)

    confirmation.attempts += 1
    if confirmation.code_hash != hash_code(confirmation.id, code):
        session.commit()  # попытку засчитываем даже при ошибке
        left = settings.code_max_attempts - confirmation.attempts
        raise DomainError("wrong_code", f"Неверный код. Осталось попыток: {left}", 422)
    confirmation.used_at = utcnow()

    actor = Actor.of(user)
    if purpose == ConfirmationPurpose.SUBMIT:
        app.submitted_at = utcnow()
        transition(session, app, S.SUBMITTED, actor, "Заявка подтверждена кодом и отправлена в банк")
    else:
        offer = active_offer(app)
        offer.status = OfferStatus.ACCEPTED
        offer.decided_at = utcnow()
        transition(
            session,
            app,
            S.SIGNED,
            actor,
            "Договор подписан кодом",
            payload={"offer_id": str(offer.id), "amount": offer.amount},
        )


def provide_info(session: Session, app: Application, actor: Actor, data: dict) -> None:
    _require_status(app, S.NEED_INFO)
    _apply_fields(app, data)
    requested = app.need_info
    app.need_info = None
    transition(
        session,
        app,
        S.CHECKING,
        actor,
        "Клиент дополнил заявку",
        payload={"requested": requested, "comment": data.get("comment")},
    )


def accept_offer(session: Session, app: Application, actor: Actor, offer_id: uuid.UUID) -> None:
    _require_status(app, S.COUNTER_OFFER)
    offer = _find_offer(app, offer_id)
    if offer.status != OfferStatus.PROPOSED:
        raise DomainError("offer_closed", "Это предложение уже неактуально", 409)
    now = utcnow()
    for other in app.offers:
        if other.status == OfferStatus.PROPOSED:
            other.status = OfferStatus.DECLINED
            other.decided_at = now
    offer.status = OfferStatus.ACCEPTED
    offer.decided_at = now
    transition(
        session,
        app,
        S.APPROVED,
        actor,
        "Клиент принял предложенные условия",
        payload={"offer_id": str(offer.id), "amount": offer.amount, "term_months": offer.term_months},
    )


def cancel(session: Session, app: Application, actor: Actor, reason: str | None) -> None:
    for offer in app.offers:
        if offer.status == OfferStatus.PROPOSED:
            offer.status = OfferStatus.DECLINED
            offer.decided_at = utcnow()
    message = "Клиент отказался от предложения" if app.status in (S.APPROVED, S.COUNTER_OFFER) else None
    transition(session, app, S.CANCELLED, actor, message or "Заявка отменена клиентом", payload={"reason": reason})


# --- банк ---------------------------------------------------------------------------------


def take(session: Session, app: Application, actor: Actor) -> None:
    if app.status in TERMINAL:
        raise DomainError("invalid_status", "Заявка уже закрыта")
    app.assignee_id = actor.user_id
    record_event(session, app, actor, "ASSIGNED", "Заявку взял в работу сотрудник банка", visible=False)


def decide_manual(session: Session, app: Application, actor: Actor, data: dict) -> None:
    """Решение сотрудника банка. Кто что может, задаёт статусная машина:
    подтвердить рекомендацию (PENDING_APPROVAL) — менеджер или андеррайтер, отказ и рисковые заявки — андеррайтер."""
    _require_status(app, S.PENDING_APPROVAL, S.MANUAL_REVIEW)
    result = data["result"]
    comment = data.get("comment")
    if result == "REJECT":
        reasons = [{"code": actor.role.value, "text": comment or "Решение кредитного специалиста"}]
        app.decision = {"result": result, "decided_by": actor.role.value, "reasons": reasons}
        transition(session, app, S.REJECTED, actor, "Банк не может одобрить заявку", payload={"reasons": reasons})
        return

    # По умолчанию — условия, рекомендованные скорингом; без рекомендации — запрошенные клиентом
    recommended = ((app.scoring or {}).get("offers") or [{}])[0]
    product = get_scoring().get_product(app.product_code)
    terms = {
        "amount": data.get("amount") or recommended.get("amount") or app.amount,
        "term_months": data.get("term_months") or recommended.get("term_months") or app.term_months,
        "rate": data.get("rate") or recommended.get("rate") or product["base_rate"],
    }
    if result == "COUNTER_OFFER" and not (data.get("amount") or data.get("term_months") or recommended):
        raise DomainError("counter_terms_required", "Для контрпредложения укажите сумму или срок", 422)

    kind = OfferKind.COUNTER if result == "COUNTER_OFFER" else OfferKind.STANDARD
    offer = add_offer(session, app, terms, kind, actor.role)
    # Сотрудник подтвердил рекомендацию скоринга — клиент видит её объяснение (почему другие условия)
    scoring = app.scoring or {}
    reasons = scoring.get("reasons", []) if scoring.get("result") == result else []
    app.decision = {"result": result, "decided_by": actor.role.value, "reasons": reasons, "comment": comment}
    target = S.COUNTER_OFFER if kind == OfferKind.COUNTER else S.APPROVED
    message = "Банк подтвердил одобрение" if target == S.APPROVED else "Банк предложил другие условия"
    transition(session, app, target, actor, message, payload={"offer_id": str(offer.id), "amount": offer.amount})


def escalate(session: Session, app: Application, actor: Actor, comment: str | None) -> None:
    """Менеджер передаёт заявку андеррайтеру, если сомневается в рекомендации скоринга."""
    transition(
        session,
        app,
        S.MANUAL_REVIEW,
        actor,
        "Заявку изучает кредитный специалист",
        payload={"comment": comment},
    )


def request_info(session: Session, app: Application, actor: Actor, items: list[dict], comment: str | None) -> None:
    app.need_info = {"items": items, "comment": comment, "requested_by": actor.role.value}
    transition(session, app, S.NEED_INFO, actor, "Банк попросил дополнить заявку", payload=app.need_info)


# --- общее --------------------------------------------------------------------------------


def add_offer(session: Session, app: Application, terms: dict, kind: OfferKind, role: Role) -> Offer:
    payment = get_scoring().calc_payment(terms["amount"], terms["term_months"], float(terms["rate"]))
    offer = Offer(
        application_id=app.id,
        kind=kind,
        status=OfferStatus.PROPOSED,
        amount=terms["amount"],
        term_months=terms["term_months"],
        rate=Decimal(str(terms["rate"])),
        monthly_payment=payment["monthly_payment"],
        created_by_role=role,
    )
    session.add(offer)
    app.offers.append(offer)
    return offer


def active_offer(app: Application) -> Offer | None:
    """Условия, которые клиент подписывает: принятое контрпредложение или единственное стандартное."""
    for status in (OfferStatus.ACCEPTED, OfferStatus.PROPOSED):
        for offer in app.offers:
            if offer.status == status and (status == OfferStatus.ACCEPTED or offer.kind == OfferKind.STANDARD):
                return offer
    return None


def _find_offer(app: Application, offer_id: uuid.UUID) -> Offer:
    for offer in app.offers:
        if offer.id == offer_id:
            return offer
    raise DomainError("offer_not_found", "Предложение не найдено", 404)
