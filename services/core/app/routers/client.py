"""Кабинет клиента: заявка от черновика до выдачи."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import service
from app.config import settings
from app.db import get_session
from app.deps import client_application, require
from app.models import Application, ConfirmationPurpose, Role, User
from app.schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationPatch,
    CancelIn,
    CodeConfirmIn,
    CodeRequestOut,
    EventOut,
    InfoProvideIn,
    PrefillIn,
)
from app.service import Actor
from app.views import client_view, events_for

router = APIRouter(prefix="/applications", tags=["Клиент: заявки"])
Client = Depends(require(Role.CLIENT))


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED, summary="Создать черновик")
def create(body: ApplicationCreate, user: User = Client, session: Session = Depends(get_session)):
    app = service.create_draft(session, user, body.product_code)
    session.commit()
    return client_view(app)


@router.get("", response_model=list[ApplicationOut], summary="Заявки моей компании")
def list_mine(user: User = Client, session: Session = Depends(get_session)):
    query = (
        select(Application)
        .where(Application.company_id == user.company_id)
        .order_by(Application.created_at.desc())
    )
    return [client_view(app) for app in session.scalars(query)]


@router.get("/{application_id}", response_model=ApplicationOut, summary="Заявка")
def get(app: Application = Depends(client_application)):
    return client_view(app)


@router.patch("/{application_id}", response_model=ApplicationOut, summary="Сохранить черновик (S3.4)")
def patch(body: ApplicationPatch, app: Application = Depends(client_application), session: Session = Depends(get_session)):
    service.update_draft(app, body.model_dump(exclude_unset=True))
    session.commit()
    return client_view(app)


@router.post("/{application_id}/prefill", response_model=ApplicationOut, summary="Заполнить анкету по ИНН (S3.1)")
def prefill(
    body: PrefillIn,
    app: Application = Depends(client_application),
    user: User = Client,
    session: Session = Depends(get_session),
):
    service.prefill(session, app, Actor.of(user), body.inn)
    session.commit()
    return client_view(app)


def _request_code(app: Application, user: User, session: Session, purpose: ConfirmationPurpose) -> CodeRequestOut:
    confirmation, code = service.request_code(session, app, user, purpose)
    session.commit()
    return CodeRequestOut(
        confirmation_id=confirmation.id,
        expires_at=confirmation.expires_at,
        demo_code=code if settings.demo_codes else None,
    )


def _confirm(body: CodeConfirmIn, app: Application, user: User, session: Session, purpose: ConfirmationPurpose):
    service.confirm_code(session, app, user, purpose, body.confirmation_id, body.code)
    session.commit()
    return client_view(app)


@router.post("/{application_id}/submit/code", response_model=CodeRequestOut, summary="Код для отправки заявки (S3.3)")
def submit_code(app: Application = Depends(client_application), user: User = Client, session: Session = Depends(get_session)):
    return _request_code(app, user, session, ConfirmationPurpose.SUBMIT)


@router.post("/{application_id}/submit/confirm", response_model=ApplicationOut, summary="Отправить заявку с кодом (S3.3)")
def submit_confirm(
    body: CodeConfirmIn,
    app: Application = Depends(client_application),
    user: User = Client,
    session: Session = Depends(get_session),
):
    return _confirm(body, app, user, session, ConfirmationPurpose.SUBMIT)


@router.post("/{application_id}/info", response_model=ApplicationOut, summary="Дополнить заявку по запросу банка")
def provide_info(
    body: InfoProvideIn,
    app: Application = Depends(client_application),
    user: User = Client,
    session: Session = Depends(get_session),
):
    service.provide_info(session, app, Actor.of(user), body.model_dump(exclude_unset=True))
    session.commit()
    return client_view(app)


@router.post(
    "/{application_id}/offers/{offer_id}/accept",
    response_model=ApplicationOut,
    summary="Принять контрпредложение (S6.2)",
)
def accept_offer(
    offer_id: uuid.UUID,
    app: Application = Depends(client_application),
    user: User = Client,
    session: Session = Depends(get_session),
):
    service.accept_offer(session, app, Actor.of(user), offer_id)
    session.commit()
    return client_view(app)


@router.post("/{application_id}/cancel", response_model=ApplicationOut, summary="Отменить заявку или отказаться от условий")
def cancel(
    body: CancelIn,
    app: Application = Depends(client_application),
    user: User = Client,
    session: Session = Depends(get_session),
):
    service.cancel(session, app, Actor.of(user), body.reason)
    session.commit()
    return client_view(app)


@router.post("/{application_id}/sign/code", response_model=CodeRequestOut, summary="Код для подписания (S7.1)")
def sign_code(app: Application = Depends(client_application), user: User = Client, session: Session = Depends(get_session)):
    return _request_code(app, user, session, ConfirmationPurpose.SIGN)


@router.post("/{application_id}/sign/confirm", response_model=ApplicationOut, summary="Подписать договор кодом (S7.1)")
def sign_confirm(
    body: CodeConfirmIn,
    app: Application = Depends(client_application),
    user: User = Client,
    session: Session = Depends(get_session),
):
    return _confirm(body, app, user, session, ConfirmationPurpose.SIGN)


@router.get("/{application_id}/events", response_model=list[EventOut], summary="История заявки для трекера (S4.5)")
def events(app: Application = Depends(client_application), user: User = Client, session: Session = Depends(get_session)):
    return events_for(session, user, application=app)
