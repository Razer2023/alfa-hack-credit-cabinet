from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import current_user
from app.errors import DomainError
from app.models import User
from app.schemas import LoginIn, TokenOut, UserOut
from app.security import create_token, verify_password

router = APIRouter(tags=["Вход"])


@router.post("/auth/login", response_model=TokenOut, summary="Вход демо-пользователя, выдача JWT")
def login(body: LoginIn, session: Session = Depends(get_session)) -> TokenOut:
    user = session.scalars(select(User).where(User.login == body.login)).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise DomainError("invalid_credentials", "Неверный логин или пароль", 401)
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut, summary="Текущий пользователь")
def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut.model_validate(user)
