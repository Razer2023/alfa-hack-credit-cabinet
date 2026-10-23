"""Фоновый конвейер: двигает заявки по автоматическим статусам.

Очередь — сама таблица заявок: обработчик выбирает заявки в статусах AUTOMATIC.
На PostgreSQL строки блокируются через SKIP LOCKED, поэтому можно запускать несколько экземпляров ядра.
После перезапуска незавершённые заявки подхватываются автоматически.
"""

import logging
import threading
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app.clients import get_integrations, get_scoring
from app.clients.base import ExternalNotFound, ExternalServiceError
from app.db import SessionLocal, utcnow
from app.models import Application, ApplicationStatus as S, Role
from app.service import SYSTEM, active_offer, record_event, snapshot, transition
from app.statemachine import AUTOMATIC

log = logging.getLogger(__name__)

# Решение скоринга — рекомендация. «Одобрить» и «контрпредложение» подтверждает сотрудник банка,
# автоматически только отказ по стоп-факторам и передача рисковых заявок андеррайтеру.
DECISIONS = {
    "APPROVE": S.PENDING_APPROVAL,
    "COUNTER_OFFER": S.PENDING_APPROVAL,
    "REJECT": S.REJECTED,
    "MANUAL_REVIEW": S.MANUAL_REVIEW,
}
MAX_RETRY_DELAY_SECONDS = 60


def step(session: Session, app: Application) -> None:
    if app.status == S.SUBMITTED:
        transition(session, app, S.CHECKING, SYSTEM)

    elif app.status == S.CHECKING:
        result = get_integrations().check_application(snapshot(app))
        if not result["complete"]:
            app.need_info = {
                "items": result["missing"],
                "comment": "Не хватает данных для рассмотрения",
                "requested_by": Role.SYSTEM.value,
            }
            transition(session, app, S.NEED_INFO, SYSTEM, payload=app.need_info)
        else:
            app.enrichment = result["enrichment"]
            transition(session, app, S.SCORING, SYSTEM)

    elif app.status == S.SCORING:
        try:
            result = get_scoring().decide(snapshot(app) | {"enrichment": app.enrichment})
            target = DECISIONS[result["result"]]
        except (KeyError, ExternalNotFound) as exc:
            raise ExternalServiceError(f"scoring: некорректный ответ ({exc})") from exc
        app.scoring = result
        if target == S.PENDING_APPROVAL:
            # Рекомендованные условия видит только банк (app.scoring); клиенту — после подтверждения
            transition(session, app, target, SYSTEM)
        else:
            reasons = result.get("reasons", [])
            app.decision = {"result": result["result"], "decided_by": "SYSTEM", "reasons": reasons}
            transition(session, app, target, SYSTEM, payload={"reasons": reasons})

    elif app.status == S.SIGNED:
        offer = active_offer(app)
        # Выдача смоделирована: реального перевода нет
        transition(
            session,
            app,
            S.ISSUED,
            SYSTEM,
            f"{offer.amount:,} ₽ зачислены на расчётный счёт".replace(",", " "),
            payload={"amount": offer.amount, "account": "40702810•••••••••0001 (демо)"},
        )


def _schedule_retry(session: Session, app: Application, error: Exception) -> None:
    app.retry_count += 1
    delay = min(2**app.retry_count, MAX_RETRY_DELAY_SECONDS)
    app.retry_at = utcnow() + timedelta(seconds=delay)
    log.warning("Заявка %s: шаг %s отложен на %s с: %s", app.number, app.status, delay, error)
    if app.retry_count == 1:
        record_event(session, app, SYSTEM, "DELAYED", "Проверка занимает больше времени, чем обычно")


def process_once(session_factory: sessionmaker = SessionLocal, delay_seconds: float = 0, limit: int = 20) -> int:
    """Один проход обработчика. Возвращает число заявок, у которых сменился статус."""
    now = utcnow()
    with session_factory() as session:
        ids = session.scalars(
            select(Application.id)
            .where(
                Application.status.in_(AUTOMATIC),
                Application.status_changed_at <= now - timedelta(seconds=delay_seconds),
                or_(Application.retry_at.is_(None), Application.retry_at <= now),
            )
            .order_by(Application.status_changed_at)
            .limit(limit)
        ).all()

    processed = 0
    for app_id in ids:
        with session_factory() as session:
            query = select(Application).where(Application.id == app_id, Application.status.in_(AUTOMATIC))
            if session.get_bind().dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            app = session.scalars(query).first()
            if app is None:
                continue
            try:
                step(session, app)
                session.commit()
                processed += 1
            except ExternalServiceError as exc:
                session.rollback()
                app = session.get(Application, app_id)
                _schedule_retry(session, app, exc)
                session.commit()
            except StaleDataError:
                session.rollback()  # заявку параллельно изменил другой процесс
    return processed


class Worker:
    def __init__(self, poll_seconds: float, delay_seconds: float):
        self._poll = poll_seconds
        self._delay = delay_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="pipeline-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                process_once(delay_seconds=self._delay)
            except Exception:
                log.exception("Ошибка фонового обработчика заявок")
            self._stop.wait(self._poll)
