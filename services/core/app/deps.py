import uuid
from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_session
from app.errors import DomainError, not_found
from app.models import Application, Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)
BANK_ROLES = (Role.MANAGER, Role.UNDERWRITER)


def user_from_token(session: Session, token: str | None) -> User:
    user_id = decode_token(token) if token else None
    user = session.get(User, user_id) if user_id else None
    if user is None:
        raise DomainError("unauthorized", "Войдите заново", 401)
    return user


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    return user_from_token(session, credentials.credentials if credentials else None)


def require(*roles: Role) -> Callable[..., User]:
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise DomainError("forbidden", "Недостаточно прав", 403)
        return user

    return dependency


def client_application(
    application_id: uuid.UUID,
    user: User = Depends(require(Role.CLIENT)),
    session: Session = Depends(get_session),
) -> Application:
    app = session.get(Application, application_id)
    # Чужие заявки не показываем и не подтверждаем, что они существуют
    if app is None or app.company_id != user.company_id:
        raise not_found()
    return app


def bank_application(
    application_id: uuid.UUID,
    user: User = Depends(require(*BANK_ROLES)),
    session: Session = Depends(get_session),
) -> Application:
    app = session.get(Application, application_id)
    if app is None:
        raise not_found()
    return app
