"""Дашборд узких мест (S8.1): сколько заявки проводят в каждом статусе и где теряется время.

Живые данные — из журнала событий ядра: длительность статуса = время до следующего перехода.
Демо-данные — синтетический массив сервиса B с готовыми длительностями этапов, чтобы на стенде
с тремя демо-заявками было что показать.
"""

from collections import Counter, defaultdict
from datetime import datetime
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import as_utc, utcnow
from app.models import Application, ApplicationEvent
from app.models import ApplicationStatus as S
from app.statemachine import STATUS_INFO

# Кто отвечает за этап: узким местом считаем только время банка и автоматики, ожидание клиента — отдельно
OWNER = {
    S.SUBMITTED: "SYSTEM",
    S.CHECKING: "SYSTEM",
    S.SCORING: "SYSTEM",
    S.PENDING_APPROVAL: "BANK",
    S.MANUAL_REVIEW: "BANK",
    S.SIGNED: "SYSTEM",
    S.NEED_INFO: "CLIENT",
    S.APPROVED: "CLIENT",
    S.COUNTER_OFFER: "CLIENT",
}
STAGES = list(OWNER)

# Этапы синтетического массива B → статусы ядра
DEMO_STAGES = {
    "checking": S.CHECKING,
    "scoring": S.SCORING,
    "manual_review": S.MANUAL_REVIEW,
    "signing": S.APPROVED,
}


def _percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def _stage(status: S, durations: list[float], waiting: list[float]) -> dict:
    info = STATUS_INFO[status]
    sla = info.sla_seconds / 60 if info.sla_seconds else None
    over = [d for d in durations + waiting if sla is not None and d > sla]
    return {
        "code": status,
        "title": info.title,
        "owner": OWNER[status],
        "sla": info.sla,
        "passed": len(durations),
        "median_minutes": round(median(durations), 1) if durations else None,
        "p90_minutes": round(_percentile(durations, 0.9), 1) if durations else None,
        "total_minutes": round(sum(durations) + sum(waiting), 1),
        "in_progress": len(waiting),
        "longest_wait_minutes": round(max(waiting), 1) if waiting else None,
        "over_sla": len(over),
    }


def _summary(source: str, applications: int, stages: list[dict], by_status: Counter) -> dict:
    # Узкое место — этап банка или автоматики, где заявки суммарно провели больше всего времени
    candidates = [s for s in stages if s["owner"] != "CLIENT" and s["total_minutes"] > 0]
    bottleneck = max(candidates, key=lambda s: s["total_minutes"], default=None)
    text = None
    if bottleneck is not None:
        share = round(100 * bottleneck["total_minutes"] / sum(s["total_minutes"] for s in candidates))
        text = f"Дольше всего заявки ждут на этапе «{bottleneck['title']}» — {share} % времени банка."
        if bottleneck["over_sla"]:
            text += f" Срок нарушен у {bottleneck['over_sla']} заявок."
    return {
        "source": source,
        "generated_at": utcnow(),
        "applications": applications,
        "stages": stages,
        "by_status": [
            {"code": code, "title": info.title, "count": by_status[code]}
            for code, info in STATUS_INFO.items()
            if by_status[code]
        ],
        "bottleneck": bottleneck["code"] if bottleneck else None,
        "bottleneck_text": text,
    }


def live(session: Session, now: datetime | None = None) -> dict:
    now = now or utcnow()
    events = session.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.type == "STATUS_CHANGED")
        .order_by(ApplicationEvent.application_id, ApplicationEvent.id)
    )
    by_app: dict = defaultdict(list)
    for event in events:
        by_app[event.application_id].append((event.to_status, as_utc(event.created_at)))

    durations: dict[S, list[float]] = defaultdict(list)
    waiting: dict[S, list[float]] = defaultdict(list)
    for changes in by_app.values():
        for (status, started), (_, finished) in zip(changes, changes[1:], strict=False):
            if status in OWNER:
                durations[status].append((finished - started).total_seconds() / 60)
        status, started = changes[-1]
        if status in OWNER:
            waiting[status].append((now - started).total_seconds() / 60)

    statuses = session.scalars(select(Application.status).where(Application.status != S.DRAFT)).all()
    stages = [_stage(s, durations[s], waiting[s]) for s in STAGES if durations[s] or waiting[s]]
    return _summary("LIVE", len(statuses), stages, Counter(statuses))


def demo(applications: list[dict]) -> dict:
    durations: dict[S, list[float]] = defaultdict(list)
    for item in applications:
        for stage, minutes in item.get("stage_minutes", {}).items():
            # 0 минут — этап заявка не проходила (например, без ручного рассмотрения)
            if stage in DEMO_STAGES and minutes:
                durations[DEMO_STAGES[stage]].append(float(minutes))
    stages = [_stage(s, durations[s], []) for s in STAGES if durations[s]]
    by_status = Counter(S(item["result"]) for item in applications if item.get("result") in S.__members__)
    return _summary("DEMO", len(applications), stages, by_status)
