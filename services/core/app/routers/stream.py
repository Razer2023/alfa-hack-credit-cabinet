"""Живые обновления статусов (S4.5): Server-Sent Events и запасной вариант с опросом."""

import asyncio
import json

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_session
from app.deps import current_user, user_from_token
from app.models import ApplicationEvent, User
from app.schemas import EventOut
from app.views import events_for

router = APIRouter(tags=["События"])

POLL_SECONDS = 1.0
PING_EVERY = 15  # циклов без событий до служебного пинга, чтобы прокси не рвали соединение


@router.get("/events", response_model=list[EventOut], summary="Новые события после after_id (опрос)")
def poll(after_id: int = 0, user: User = Depends(current_user), session: Session = Depends(get_session)):
    return events_for(session, user, after_id=after_id)


def _latest_event_id() -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.max(ApplicationEvent.id))) or 0


def _authenticate(token: str) -> User:
    with SessionLocal() as session:
        return user_from_token(session, token)


def _fetch(user: User, after_id: int) -> list[EventOut]:
    with SessionLocal() as session:
        return events_for(session, user, after_id=after_id)


@router.get(
    "/stream",
    summary="Поток событий (text/event-stream)",
    description=(
        "EventSource в браузере не умеет передавать заголовки, поэтому JWT передаётся в параметре token. "
        "Без after_id поток начинается с текущего момента; при переподключении браузер сам шлёт Last-Event-ID."
    ),
    response_class=StreamingResponse,
)
async def stream(
    request: Request,
    token: str = Query(...),
    after_id: int | None = None,
    last_event_id: str | None = Header(None),
):
    user = await run_in_threadpool(_authenticate, token)
    if last_event_id and last_event_id.isdigit():
        cursor = int(last_event_id)
    elif after_id is not None:
        cursor = after_id
    else:
        cursor = await run_in_threadpool(_latest_event_id)

    async def generate():
        nonlocal cursor
        idle = 0
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            events = await run_in_threadpool(_fetch, user, cursor)
            for event in events:
                cursor = event.id
                data = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                yield f"id: {event.id}\nevent: application\ndata: {data}\n\n"
            idle = 0 if events else idle + 1
            if idle >= PING_EVERY:
                idle = 0
                yield ": ping\n\n"
            await asyncio.sleep(POLL_SECONDS)

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(generate(), media_type="text/event-stream", headers=headers)
