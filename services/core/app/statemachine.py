"""Статусная модель заявки: единственный источник правды о допустимых переходах."""

from dataclasses import dataclass

from app.models import ApplicationStatus as S
from app.models import Role

# (из, в) → кто может выполнить переход
TRANSITIONS: dict[tuple[S, S], frozenset[Role]] = {
    (S.DRAFT, S.SUBMITTED): frozenset({Role.CLIENT}),
    (S.DRAFT, S.CANCELLED): frozenset({Role.CLIENT}),
    (S.SUBMITTED, S.CHECKING): frozenset({Role.SYSTEM}),
    (S.CHECKING, S.NEED_INFO): frozenset({Role.SYSTEM}),
    (S.CHECKING, S.SCORING): frozenset({Role.SYSTEM}),
    (S.NEED_INFO, S.CHECKING): frozenset({Role.CLIENT}),
    (S.NEED_INFO, S.CANCELLED): frozenset({Role.CLIENT}),
    (S.SCORING, S.APPROVED): frozenset({Role.SYSTEM}),
    (S.SCORING, S.COUNTER_OFFER): frozenset({Role.SYSTEM}),
    (S.SCORING, S.REJECTED): frozenset({Role.SYSTEM}),
    (S.SCORING, S.MANUAL_REVIEW): frozenset({Role.SYSTEM}),
    (S.MANUAL_REVIEW, S.APPROVED): frozenset({Role.UNDERWRITER}),
    (S.MANUAL_REVIEW, S.COUNTER_OFFER): frozenset({Role.UNDERWRITER}),
    (S.MANUAL_REVIEW, S.REJECTED): frozenset({Role.UNDERWRITER}),
    (S.MANUAL_REVIEW, S.NEED_INFO): frozenset({Role.UNDERWRITER, Role.MANAGER}),
    (S.COUNTER_OFFER, S.APPROVED): frozenset({Role.CLIENT}),
    (S.COUNTER_OFFER, S.CANCELLED): frozenset({Role.CLIENT}),
    (S.APPROVED, S.SIGNED): frozenset({Role.CLIENT}),
    (S.APPROVED, S.CANCELLED): frozenset({Role.CLIENT}),
    (S.SIGNED, S.ISSUED): frozenset({Role.SYSTEM}),
}

# Статусы, которые двигает фоновый обработчик без участия людей
AUTOMATIC = (S.SUBMITTED, S.CHECKING, S.SCORING, S.SIGNED)
TERMINAL = frozenset({S.REJECTED, S.ISSUED, S.CANCELLED})


@dataclass(frozen=True)
class StatusInfo:
    title: str
    hint: str  # что происходит и что делать клиенту — простым языком


STATUS_INFO: dict[S, StatusInfo] = {
    S.DRAFT: StatusInfo("Черновик", "Заполните заявку и отправьте её на рассмотрение"),
    S.SUBMITTED: StatusInfo("Отправлена", "Заявка принята, скоро начнём проверку"),
    S.CHECKING: StatusInfo("Проверка данных", "Проверяем данные компании в ЕГРЮЛ, ФНС и бюро кредитных историй"),
    S.NEED_INFO: StatusInfo("Нужны данные", "Банку не хватает информации — дополните заявку"),
    S.SCORING: StatusInfo("Оценка", "Оцениваем заявку и подбираем условия"),
    S.MANUAL_REVIEW: StatusInfo("У специалиста", "Заявку изучает кредитный специалист"),
    S.APPROVED: StatusInfo("Одобрена", "Проверьте условия и подпишите договор"),
    S.COUNTER_OFFER: StatusInfo(
        "Другие условия", "Банк готов выдать кредит на других условиях — посмотрите предложение"
    ),
    S.REJECTED: StatusInfo("Отказ", "Банк не может одобрить заявку сейчас"),
    S.SIGNED: StatusInfo("Подписана", "Договор подписан, перечисляем деньги"),
    S.ISSUED: StatusInfo("Деньги зачислены", "Кредит выдан, деньги на расчётном счёте"),
    S.CANCELLED: StatusInfo("Отменена", "Заявка отменена"),
}

# Действия, доступные в статусе: подсказка интерфейсу, какие кнопки показывать
CLIENT_ACTIONS: dict[S, tuple[str, ...]] = {
    S.DRAFT: ("EDIT", "PREFILL", "SUBMIT", "CANCEL"),
    S.NEED_INFO: ("PROVIDE_INFO", "CANCEL"),
    S.COUNTER_OFFER: ("ACCEPT_OFFER", "DECLINE_OFFER"),
    S.APPROVED: ("SIGN", "CANCEL"),
}
BANK_ACTIONS: dict[S, tuple[str, ...]] = {
    S.MANUAL_REVIEW: ("TAKE", "DECIDE", "REQUEST_INFO"),
}


def allowed_roles(src: S, dst: S) -> frozenset[Role] | None:
    return TRANSITIONS.get((src, dst))


def actions_for(status: S, role: Role) -> list[str]:
    table = CLIENT_ACTIONS if role == Role.CLIENT else BANK_ACTIONS
    return list(table.get(status, ()))


def to_mermaid() -> str:
    """Диаграмма состояний для документации (генерируется, руками не правится)."""
    lines = ["stateDiagram-v2", "    [*] --> DRAFT"]
    for (src, dst), roles in TRANSITIONS.items():
        who = ", ".join(sorted(r.value for r in roles))
        lines.append(f"    {src.value} --> {dst.value}: {who}")
    lines += [f"    {s.value} --> [*]" for s in sorted(TERMINAL)]
    return "\n".join(lines)
