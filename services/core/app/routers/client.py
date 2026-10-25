"""Кабинет клиента: заявка от черновика до выдачи."""

import uuid
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, Request, status
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
    DocumentRequestOut,
    EventOut,
    InfoProvideIn,
    MessageIn,
    MessageOut,
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


@router.get(
    "/{application_id}/documents",
    response_model=list[DocumentRequestOut],
    summary="Документы, которые запросил банк (S4.7)",
)
def documents(app: Application = Depends(client_application), session: Session = Depends(get_session)):
    return service.list_documents(session, app)


@router.post(
    "/{application_id}/documents/{request_id}/{code}",
    response_model=DocumentRequestOut,
    summary="Загрузить файл по запросу банка (S4.7)",
    description=(
        "Тело запроса — сам файл (PDF, JPEG или PNG до 5 МБ), тип — в Content-Type, "
        "имя файла — в заголовке X-Filename (URL-encoded)."
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {t: {"schema": {"type": "string", "format": "binary"}} for t in ("application/pdf", "image/jpeg", "image/png")},
        }
    },
)
async def upload(
    request_id: str,
    code: str,
    request: Request,
    content_type: str = Header("application/octet-stream"),
    x_filename: str = Header("document"),
    app: Application = Depends(client_application),
    user: User = Client,
    session: Session = Depends(get_session),
):
    payload = await request.body()
    result = service.upload_document(
        session, app, Actor.of(user), request_id, code, unquote(x_filename), content_type, payload
    )
    session.commit()
    return result


@router.get("/{application_id}/messages", response_model=list[MessageOut], summary="Переписка с банком (S4.10)")
def messages(app: Application = Depends(client_application), session: Session = Depends(get_session)):
    return [service.message_view(m) for m in service.list_messages(session, app)]


@router.post(
    "/{application_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Написать менеджеру по заявке (S4.10)",
)
def send_message(
    body: MessageIn,
    app: Application = Depends(client_application),
    user: User = Client,
    session: Session = Depends(get_session),
):
    message = service.post_message(session, app, user, body.text)
    session.commit()
    return service.message_view(message)
