"""Дашборд узких мест для руководителя и сотрудников банка (S8.1)."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import dashboard
from app.clients import get_integrations
from app.db import get_session
from app.deps import BANK_ROLES, require
from app.schemas import DashboardOut

router = APIRouter(prefix="/bank/dashboard", tags=["Банк: дашборд"], dependencies=[Depends(require(*BANK_ROLES))])


@router.get("", response_model=DashboardOut, summary="Где заявки теряют время (S8.1)")
def bottlenecks(
    source: Literal["LIVE", "DEMO"] = Query("LIVE", description="LIVE — журнал ядра, DEMO — синтетический массив сервиса B"),
    session: Session = Depends(get_session),
) -> dict:
    if source == "DEMO":
        return dashboard.demo(get_integrations().dashboard_applications())
    return dashboard.live(session)
