"""Преобразование моделей в ответы API."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, ApplicationEvent, Role, User
from app.schemas import ApplicationBankOut, ApplicationOut, CompanyOut, EventOut, OfferOut, StatusOut
from app.statemachine import STATUS_INFO, actions_for


def _common(app: Application, role: Role) -> dict:
    info = STATUS_INFO[app.status]
    return {
        "id": app.id,
        "number": app.number,
        "status": StatusOut(code=app.status, title=info.title, hint=info.hint),
        "allowed_actions": actions_for(app.status, role),
        "product_code": app.product_code,
        "amount": app.amount,
        "term_months": app.term_months,
        "purpose": app.purpose,
        "form": app.form,
        "need_info": app.need_info,
        "decision": app.decision,
        "offers": [OfferOut.model_validate(offer) for offer in app.offers],
        "company": CompanyOut.model_validate(app.company),
        "created_at": app.created_at,
        "updated_at": app.updated_at,
        "submitted_at": app.submitted_at,
        "status_changed_at": app.status_changed_at,
    }


def client_view(app: Application) -> ApplicationOut:
    return ApplicationOut(**_common(app, Role.CLIENT))


def bank_view(app: Application, user: User) -> ApplicationBankOut:
    return ApplicationBankOut(
        **_common(app, user.role),
        enrichment=app.enrichment,
        scoring=app.scoring,
        assignee_id=app.assignee_id,
    )


def events_for(session: Session, user: User, after_id: int = 0, application: Application | None = None, limit: int = 200) -> list[EventOut]:
    """События, которые видит пользователь: клиент — только свои и только клиентские."""
    query = select(ApplicationEvent).where(ApplicationEvent.id > after_id).order_by(ApplicationEvent.id).limit(limit)
    if application is not None:
        query = query.where(ApplicationEvent.application_id == application.id)
    if user.role == Role.CLIENT:
        query = query.where(
            ApplicationEvent.company_id == user.company_id,
            ApplicationEvent.visible_to_client.is_(True),
        )
    return [EventOut.model_validate(event) for event in session.scalars(query)]
