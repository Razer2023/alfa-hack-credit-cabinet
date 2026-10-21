from app.models import ApplicationStatus as S
from app.models import Role
from app.statemachine import AUTOMATIC, STATUS_INFO, TERMINAL, TRANSITIONS, to_mermaid


def test_every_status_has_description():
    assert set(STATUS_INFO) == set(S)


def test_terminal_statuses_have_no_exits():
    assert not [pair for pair in TRANSITIONS if pair[0] in TERMINAL]


def test_automatic_statuses_are_moved_by_system():
    for status in AUTOMATIC:
        exits = [roles for (src, _), roles in TRANSITIONS.items() if src == status]
        assert exits and all(Role.SYSTEM in roles for roles in exits)


def test_every_status_is_reachable_from_draft():
    reached, frontier = {S.DRAFT}, [S.DRAFT]
    while frontier:
        current = frontier.pop()
        for src, dst in TRANSITIONS:
            if src == current and dst not in reached:
                reached.add(dst)
                frontier.append(dst)
    assert reached == set(S)


def test_mermaid_lists_all_transitions():
    diagram = to_mermaid()
    assert diagram.count("-->") == len(TRANSITIONS) + 1 + len(TERMINAL)
