"""Операции с заявкой. Каждая меняет статус только через transition(), чтобы все переходы попадали в журнал."""

import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clients import get_integrations, get_scoring
from app.clients.base import ExternalNotFound, ExternalRejected, ExternalServiceError
from app.config import settings
from app.db import as_utc, utcnow
from app.errors import DomainError
from app.models import (
    Application,
    ApplicationEvent,
    ApplicationStatus as S,
    Confirmation,
    ConfirmationPurpose,
    Message,
    Offer,
    OfferKind,
    OfferStatus,
    Role,
    User,
)
from app.security import hash_code, new_code
from app.statemachine import STATUS_INFO, TERMINAL, allowed_roles

log = logging.getLogger(__name__)

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
    ensure_transition(app, to, actor)
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


def ensure_transition(app: Application, to: S, actor: Actor) -> None:
    """Проверка перехода без его выполнения — до обращения во внешние сервисы."""
    roles = allowed_roles(app.status, to)
    if roles is None:
        raise DomainError("invalid_transition", f"Действие недоступно в статусе «{STATUS_INFO[app.status].title}»")
    if actor.role not in roles:
        raise DomainError("forbidden", "Недостаточно прав для этого действия", 403)


def _require_status(app: Application, *statuses: S) -> None:
    if app.status not in statuses:
        raise DomainError("invalid_status", f"Действие недоступно в статусе «{STATUS_INFO[app.status].title}»")


def _apply_fields(app: Application, data: dict) -> None:
    for field in ("amount", "term_months", "purpose"):
        if data.get(field) is not None:
            setattr(app, field, data[field])
    if data.get("extra"):
        app.form = {**app.form, "extra": {**app.form.get("extra", {}), **data["extra"]}}


def snapshot(app: Application) -> dict:
    """Данные заявки для внешних сервисов (контракты B и C)."""
    company = {name: field["value"] for name, field in (app.form.get("company") or {}).items()}
    return {
        "application_id": str(app.id),
        "inn": app.company.inn,
        "application": {
            "product_code": app.product_code,
            "amount": app.amount,
            "term_months": app.term_months,
            "purpose": app.purpose,
        },
        "company": company,
        "extra": app.form.get("extra", {}),
    }


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
    _require_documents_uploaded(app)
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
    # Менеджер, взявший заявку, становится контактом клиента
    if actor.role == Role.MANAGER and app.manager_id != actor.user_id:
        _set_manager(session, app, session.get(User, actor.user_id), actor)


def assign_manager(session: Session, app: Application) -> None:
    """Персональный менеджер — наименее загруженный: меньше всего незакрытых заявок (S4.9)."""
    if app.manager_id is not None:
        return
    open_count = (
        select(func.count(Application.id))
        .where(Application.manager_id == User.id, Application.status.not_in(TERMINAL))
        .scalar_subquery()
    )
    manager = session.scalars(
        select(User).where(User.role == Role.MANAGER).order_by(open_count, User.login).limit(1)
    ).first()
    if manager is not None:
        _set_manager(session, app, manager, SYSTEM)


def _set_manager(session: Session, app: Application, manager: User, actor: Actor) -> None:
    app.manager_id = manager.id
    app.manager = manager
    position = f", {manager.position.lower()}" if manager.position else ""
    record_event(session, app, actor, "MANAGER_ASSIGNED", f"Заявку ведёт {manager.full_name}{position}")


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

    # S5.4: условия сотрудника проходят ту же политику, что и автоматическое решение
    check = check_terms(app, terms)
    override = not check.get("allowed", True)
    if override:
        _require_override_right(actor, check, comment)

    kind = OfferKind.COUNTER if result == "COUNTER_OFFER" else OfferKind.STANDARD
    offer = add_offer(session, app, terms, kind, actor.role)
    # Сотрудник подтвердил рекомендацию скоринга — клиент видит её объяснение (почему другие условия)
    scoring = app.scoring or {}
    reasons = scoring.get("reasons", []) if scoring.get("result") == result else []
    checks = check.get("checks", [])
    app.decision = {
        "result": result,
        "decided_by": actor.role.value,
        "reasons": reasons,
        "comment": comment,
        "checks": checks,
        "override": override,
    }
    target = S.COUNTER_OFFER if kind == OfferKind.COUNTER else S.APPROVED
    message = "Банк подтвердил одобрение" if target == S.APPROVED else "Банк предложил другие условия"
    transition(session, app, target, actor, message, payload={"offer_id": str(offer.id), "amount": offer.amount})
    if override:
        # Отступление от кредитной политики — только в истории для банка, клиенту не показывается
        record_event(
            session,
            app,
            actor,
            "POLICY_OVERRIDE",
            f"Условия выданы с отступлением от политики: {comment}",
            payload={"checks": checks},
            visible=False,
        )


def check_terms(app: Application, terms: dict) -> dict:
    """Проверка условий в скоринге. Если скоринг недоступен, решение не блокируем — только предупреждаем."""
    request = snapshot(app) | {"enrichment": app.enrichment or {}, "terms": terms}
    try:
        return get_scoring().check_offer(request)
    except (ExternalServiceError, ExternalNotFound) as exc:
        log.warning("Заявка %s: проверка условий недоступна: %s", app.number, exc)
        return {
            "allowed": True,
            "terms": terms,
            "checks": [
                {
                    "code": "CHECK_UNAVAILABLE",
                    "level": "warning",
                    "text": "Скоринг недоступен — условия не проверены по политике банка",
                }
            ],
            "suggestion": None,
        }


def _require_override_right(actor: Actor, check: dict, comment: str | None) -> None:
    """Условия не проходят политику: менеджер подтвердить не может, андеррайтер — только с обоснованием."""
    problems = "; ".join(c["text"] for c in check.get("checks", []) if c.get("level") == "error")
    problems = problems or "условия не проходят кредитную политику"
    suggestion = check.get("suggestion")
    hint = (
        f" Допустимо до {suggestion['amount']:,} ₽ на {suggestion['term_months']} мес.".replace(",", " ")
        if suggestion
        else ""
    )
    if actor.role != Role.UNDERWRITER:
        raise DomainError(
            "offer_not_allowed",
            f"Условия не проходят политику банка: {problems}.{hint} Измените условия или передайте заявку андеррайтеру",
            422,
        )
    if not (comment or "").strip():
        raise DomainError(
            "override_comment_required",
            f"Условия не проходят политику банка: {problems}.{hint} "
            "Чтобы выдать их с отступлением, обоснуйте решение в комментарии",
            422,
        )


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


# --- чат по заявке (S4.10) ----------------------------------------------------------------


def post_message(session: Session, app: Application, user: User, text: str) -> Message:
    if app.status == S.DRAFT:
        raise DomainError("chat_unavailable", "Переписка откроется после отправки заявки", 409)
    text = text.strip()
    if not text:
        raise DomainError("empty_message", "Напишите сообщение", 422)
    message = Message(application_id=app.id, author_id=user.id, author_role=user.role, text=text, author=user)
    session.add(message)
    session.flush()
    # Событие в журнале доставляет сообщение собеседнику по тому же SSE-потоку, что и статусы
    record_event(
        session,
        app,
        Actor.of(user),
        "MESSAGE",
        f"{message_view(message)['author_name']}: {text[:120]}",
        payload={"message_id": message.id},
    )
    return message


def list_messages(session: Session, app: Application) -> list[Message]:
    return list(
        session.scalars(select(Message).where(Message.application_id == app.id).order_by(Message.id))
    )


def message_view(message: Message) -> dict:
    author = message.author
    return {
        "id": message.id,
        "author_role": message.author_role,
        "author_name": author.company.name if message.author_role == Role.CLIENT and author.company else author.full_name,
        "text": message.text,
        "created_at": message.created_at,
    }


# --- подбор продукта по цели (S1.2) -------------------------------------------------------


def _same_purpose(a: str, b: str) -> bool:
    # «Закупка» и «Закупка товара» — одна цель: короткая формулировка совпадает с началом длинной
    a, b = a.strip().casefold(), b.strip().casefold()
    return a.startswith(b) or b.startswith(a)


def product_purposes(products: list[dict]) -> list[str]:
    """Цели из каталога без повторов: из похожих формулировок остаётся более подробная."""
    goals: list[str] = []
    for product in products:
        for purpose in product.get("purposes", []):
            same = next((g for g in goals if _same_purpose(g, purpose)), None)
            if same is None:
                goals.append(purpose)
            elif len(purpose) > len(same):
                goals[goals.index(same)] = purpose
    return goals


def match_products(products: list[dict], purpose: str, amount: int | None, term_months: int | None) -> list[dict]:
    """Правила подбора прозрачны: цель из каталога, сумма и срок в рамках продукта, затем ставка."""
    result = []
    for product in products:
        purpose_match = any(_same_purpose(p, purpose) for p in product.get("purposes", []))
        notes = [f"Подходит для цели «{purpose.strip()}»"] if purpose_match else ["Продукт для других целей"]
        fits = purpose_match
        if amount is not None and not product["min_amount"] <= amount <= product["max_amount"]:
            fits = False
            limit = "ниже минимума" if amount < product["min_amount"] else "выше максимума"
            notes.append(
                f"Сумма {_rub(amount)} {limit}: продукт от {_rub(product['min_amount'])} до {_rub(product['max_amount'])}"
            )
        if term_months is not None and not product["min_term_months"] <= term_months <= product["max_term_months"]:
            fits = False
            notes.append(f"Срок — от {product['min_term_months']} до {product['max_term_months']} мес.")
        result.append({"product": product, "purpose_match": purpose_match, "fits": fits, "notes": notes})

    best = min((r for r in result if r["fits"]), key=lambda r: r["product"]["base_rate"], default=None)
    for item in result:
        item["recommended"] = item is best
    if best is not None and sum(r["fits"] for r in result) > 1:
        best["notes"].append("Самая низкая ставка среди подходящих")
    # Сначала лучший, затем подходящие, затем совпавшие по цели, остальные — в порядке каталога
    return sorted(result, key=lambda r: (not r["recommended"], not r["fits"], not r["purpose_match"]))


# --- предоценка (S2.1) --------------------------------------------------------------------
# Тот же путь, что у заявки: профиль и проверки в B, решение в C — но без сохранения результата.

PRECHECK_TEXT = {
    "APPROVE": ("HIGH", "Шансы высокие"),
    "COUNTER_OFFER": ("MEDIUM", "Одобрим, но на других условиях"),
    "MANUAL_REVIEW": ("MEDIUM", "Решение примет кредитный специалист"),
    "REJECT": ("LOW", "Сейчас одобрить вряд ли получится"),
}


def precheck(user: User, data: dict) -> dict:
    scoring, integrations = get_scoring(), get_integrations()
    try:
        product = scoring.get_product(data["product_code"])
    except ExternalNotFound:
        raise DomainError("unknown_product", "Такого кредитного продукта нет", 422) from None
    inn = user.company.inn
    try:
        fields = integrations.company_profile(inn)["fields"]
    except ExternalNotFound:
        raise DomainError("company_not_found", "Не нашли компанию по ИНН — оценка недоступна", 404) from None
    company = {name: field["value"] for name, field in fields.items()}

    def snapshot_for(amount: int, term: int) -> dict:
        application = {"product_code": product["code"], "amount": amount, "term_months": term, "purpose": "Предоценка"}
        return {"application_id": "precheck", "inn": inn, "application": application, "company": company, "extra": {}}

    enrichment = integrations.check_application(snapshot_for(product["max_amount"], product["max_term_months"]))["enrichment"]

    def decide(amount: int, term: int) -> dict:
        return scoring.decide(snapshot_for(amount, term) | {"enrichment": enrichment})

    # Максимум: просим верхнюю границу продукта — скоринг либо согласится, либо назовёт лимит
    best = decide(product["max_amount"], product["max_term_months"])
    best_offer = (best.get("offers") or [None])[0] if best["result"] in ("APPROVE", "COUNTER_OFFER") else None

    asked = data.get("amount") and data.get("term_months")
    result = decide(data["amount"], data["term_months"]) if asked else best
    offer = (result.get("offers") or [None])[0] if result["result"] in ("APPROVE", "COUNTER_OFFER") else None

    # Лимит скоринг считает с учётом запроса, поэтому «максимум» не должен быть меньше уже предложенной суммы
    if offer and (best_offer is None or offer["amount"] > best_offer["amount"]):
        best_offer = offer

    chance, title = PRECHECK_TEXT[result["result"]]
    terms = None
    if offer:
        payment = scoring.calc_payment(offer["amount"], offer["term_months"], float(offer["rate"]))
        terms = {
            "amount": offer["amount"],
            "term_months": offer["term_months"],
            "rate": offer["rate"],
            "monthly_payment": payment["monthly_payment"],
        }
    return {
        "product_code": product["code"],
        "chance": chance,
        "title": title,
        "explanation": _precheck_explanation(result["result"], terms, asked),
        "max_amount": best_offer["amount"] if best_offer else None,
        "max_amount_term_months": best_offer["term_months"] if best_offer else None,
        "terms": terms,
        "reasons": [reason["text"] for reason in result.get("reasons", [])],
    }


def _rub(value: int) -> str:
    return f"{value:,} ₽".replace(",", " ")


def _precheck_explanation(result: str, terms: dict | None, asked: bool) -> str:
    if result == "APPROVE" and terms:
        what = "эту сумму" if asked else f"до {_rub(terms['amount'])}"
        return f"Скорее всего одобрим {what} на {terms['term_months']} мес. Окончательно условия подтвердит менеджер."
    if result == "COUNTER_OFFER" and terms:
        return (
            f"Запрошенные условия вряд ли пройдут, но можем предложить {_rub(terms['amount'])} "
            f"на {terms['term_months']} мес. Это можно указать сразу в заявке."
        )
    if result == "MANUAL_REVIEW":
        return "Заявку посмотрит кредитный специалист — могут понадобиться документы. Срок решения — до 1 рабочего дня."
    return "Можно уменьшить сумму, выбрать другой продукт или вернуться позже."


# --- документы (S4.4, S4.7) ---------------------------------------------------------------
# Файлы хранит сервис B, ядро ведёт сам запрос: что нужно, зачем (J9) и дошло ли до клиента.


def request_documents(session: Session, app: Application, actor: Actor, asks: list[dict], comment: str | None) -> None:
    """Сотрудник просит документы и для каждого пишет, зачем он нужен. Заявка уходит клиенту (NEED_INFO)."""
    ensure_transition(app, S.NEED_INFO, actor)  # до создания запроса в B, чтобы не оставлять сирот
    body = {
        "application_id": str(app.id),
        "inn": app.company.inn,
        "comment": comment,
        "items": [{"code": f"doc{n}", "title": ask["title"]} for n, ask in enumerate(asks, 1)],
    }
    try:
        request = get_integrations().create_document_request(body)
    except ExternalRejected as exc:
        raise DomainError("document_request_rejected", exc.message, 422) from None
    items = [
        {
            "field": f"document:{request['id']}:{item['code']}",
            "message": item["title"],
            "reason": ask["reason"],
            "document": {"request_id": request["id"], "code": item["code"]},
        }
        for item, ask in zip(request["items"], asks, strict=True)
    ]
    app.need_info = {"items": items, "comment": comment, "requested_by": actor.role.value}
    titles = ", ".join(ask["title"] for ask in asks)
    transition(session, app, S.NEED_INFO, actor, f"Банк запросил документы: {titles}", payload=app.need_info)


def _requested_documents(app: Application) -> list[dict]:
    return [item for item in (app.need_info or {}).get("items", []) if item.get("document")]


def _require_documents_uploaded(app: Application) -> None:
    requested = _requested_documents(app)
    if not requested:
        return
    status = {
        (request["id"], item["code"]): item["status"]
        for request in get_integrations().list_document_requests(str(app.id))
        for item in request["items"]
    }
    missing = [
        item["message"]
        for item in requested
        if status.get((item["document"]["request_id"], item["document"]["code"])) != "RECEIVED"
    ]
    if missing:
        raise DomainError("documents_missing", f"Загрузите документы: {', '.join(missing)}", 422)


def upload_document(
    session: Session,
    app: Application,
    actor: Actor,
    request_id: str,
    code: str,
    filename: str,
    content_type: str,
    payload: bytes,
) -> dict:
    _require_status(app, S.NEED_INFO)
    item = next(
        (i for i in _requested_documents(app) if i["document"] == {"request_id": request_id, "code": code}),
        None,
    )
    if item is None:
        raise DomainError("document_not_requested", "Банк не запрашивал такой документ", 404)
    try:
        request = get_integrations().upload_document(request_id, code, filename, content_type, payload)
    except ExternalRejected as exc:
        raise DomainError("document_rejected", exc.message, 422) from None
    record_event(
        session,
        app,
        actor,
        "DOCUMENT_UPLOADED",
        f"Загружен документ: {item['message']}",
        payload={"request_id": request_id, "code": code, "filename": filename},
    )
    return _with_reasons(session, app, request)


def list_documents(session: Session, app: Application) -> list[dict]:
    requests = get_integrations().list_document_requests(str(app.id))
    return [_with_reasons(session, app, request) for request in requests]


def download_document(session: Session, app: Application, request_id: str, code: str) -> tuple[bytes, str, str]:
    if request_id not in {r["id"] for r in get_integrations().list_document_requests(str(app.id))}:
        raise DomainError("not_found", "Документ не найден", 404)
    try:
        payload, content_type, stored_name = get_integrations().download_document(request_id, code)
    except ExternalNotFound:
        raise DomainError("not_found", "Файл ещё не загружен", 404) from None
    original = _document_journal(session, app)[1].get((request_id, code))
    return payload, content_type, original or stored_name


def _document_journal(session: Session, app: Application) -> tuple[dict, dict]:
    """Сервис B хранит только название и имя файла латиницей. Пояснение «зачем» и исходное имя файла
    (с кириллицей) ядро берёт из журнала заявки: (request_id, code) → reason / filename."""
    reasons: dict[tuple[str, str], str | None] = {}
    filenames: dict[tuple[str, str], str] = {}
    events = session.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == app.id)
        .where((ApplicationEvent.to_status == S.NEED_INFO) | (ApplicationEvent.type == "DOCUMENT_UPLOADED"))
        .order_by(ApplicationEvent.id)
    )
    for event in events:
        payload = event.payload or {}
        if event.type == "DOCUMENT_UPLOADED":
            filenames[(payload["request_id"], payload["code"])] = payload["filename"]
            continue
        for item in payload.get("items", []):
            if item.get("document"):
                reasons[(item["document"]["request_id"], item["document"]["code"])] = item.get("reason")
    return reasons, filenames


def _with_reasons(session: Session, app: Application, request: dict) -> dict:
    reasons, filenames = _document_journal(session, app)
    items = [
        item
        | {
            "reason": reasons.get((request["id"], item["code"])),
            "filename": filenames.get((request["id"], item["code"]), item.get("filename")),
        }
        for item in request["items"]
    ]
    return request | {"items": items}


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
