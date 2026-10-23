"""Рабочее место банка: очередь заявок менеджера и карточка андеррайтера."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import service
from app.db import get_session
from app.deps import BANK_ROLES, bank_application, require
from app.errors import DomainError
from app.models import Application, ApplicationStatus, Role, User
from app.schemas import ApplicationBankOut, DecisionIn, EscalateIn, EventOut, InfoRequestIn, OfferCheckIn, OfferCheckOut
from app.service import Actor
from app.views import bank_view, events_for

router = APIRouter(prefix="/bank/applications", tags=["Банк: заявки"])
Staff = Depends(require(*BANK_ROLES))


@router.get("", response_model=list[ApplicationBankOut], summary="Очередь заявок (S4.3)")
def queue(
    status: list[ApplicationStatus] = Query(default=[], description="Фильтр по статусам; пусто — все, кроме черновиков"),
    mine: bool = Query(False, description="Только заявки, взятые мной в работу"),
    user: User = Staff,
    session: Session = Depends(get_session),
):
    query = select(Application).order_by(Application.status_changed_at.desc()).limit(200)
    if status:
        query = query.where(Application.status.in_(status))
    else:
        query = query.where(Application.status != ApplicationStatus.DRAFT)
    if mine:
        query = query.where(Application.assignee_id == user.id)
    return [bank_view(app, user) for app in session.scalars(query)]


@router.get("/{application_id}", response_model=ApplicationBankOut, summary="Карточка заявки (S5.3)")
def card(app: Application = Depends(bank_application), user: User = Staff):
    return bank_view(app, user)


@router.get("/{application_id}/events", response_model=list[EventOut], summary="Полная история заявки")
def events(app: Application = Depends(bank_application), user: User = Staff, session: Session = Depends(get_session)):
    return events_for(session, user, application=app)


@router.post("/{application_id}/take", response_model=ApplicationBankOut, summary="Взять заявку в работу")
def take(app: Application = Depends(bank_application), user: User = Staff, session: Session = Depends(get_session)):
    service.take(session, app, Actor.of(user))
    session.commit()
    return bank_view(app, user)


@router.post(
    "/{application_id}/decision",
    response_model=ApplicationBankOut,
    summary="Решение сотрудника банка",
    description=(
        "Подтвердить рекомендацию скоринга (статус PENDING_APPROVAL) может менеджер или андеррайтер. "
        "Отказ и решения по рисковым заявкам (MANUAL_REVIEW) — только андеррайтер. "
        "Без суммы, срока и ставки берутся условия, рекомендованные скорингом."
    ),
)
def decide(
    body: DecisionIn,
    app: Application = Depends(bank_application),
    user: User = Staff,
    session: Session = Depends(get_session),
):
    service.decide_manual(session, app, Actor.of(user), body.model_dump())
    session.commit()
    return bank_view(app, user)


@router.post(
    "/{application_id}/offer-check",
    response_model=OfferCheckOut,
    summary="Проверить условия до решения (S5.4)",
    description=(
        "Прогоняет условия сотрудника через скоринг по той же политике, что и автоматическое решение. "
        "Ничего не меняет в заявке: веб показывает предупреждения, пока сотрудник вводит условия."
    ),
)
def offer_check(
    body: OfferCheckIn,
    app: Application = Depends(bank_application),
    user: User = Staff,
):
    if not app.enrichment:
        raise DomainError("not_checked_yet", "Заявка ещё не прошла проверки — условия оценить нельзя", 409)
    return service.check_terms(app, body.model_dump())


@router.post("/{application_id}/escalate", response_model=ApplicationBankOut, summary="Передать андеррайтеру")
def escalate(
    body: EscalateIn,
    app: Application = Depends(bank_application),
    user: User = Depends(require(Role.MANAGER)),
    session: Session = Depends(get_session),
):
    service.escalate(session, app, Actor.of(user), body.comment)
    session.commit()
    return bank_view(app, user)


@router.post("/{application_id}/info-request", response_model=ApplicationBankOut, summary="Запросить данные у клиента (S4.4)")
def info_request(
    body: InfoRequestIn,
    app: Application = Depends(bank_application),
    user: User = Staff,
    session: Session = Depends(get_session),
):
    items = [item.model_dump() for item in body.items]
    service.request_info(session, app, Actor.of(user), items, body.comment)
    session.commit()
    return bank_view(app, user)
