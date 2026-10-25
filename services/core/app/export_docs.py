"""Генерирует контракт и диаграмму из кода: python -m app.export_docs

- contracts/core.yaml — OpenAPI ядра (по нему работает веб, область D);
- docs/architecture/statuses.md — диаграмма состояний заявки.
CI проверяет, что сгенерированные файлы закоммичены и не устарели.
"""

from pathlib import Path

import yaml

from app.main import app
from app.statemachine import STATUS_INFO, TERMINAL, to_mermaid

REPO = Path(__file__).resolve().parents[3]


def statuses_markdown() -> str:
    rows = "\n".join(
        f"| `{status.value}` | {info.title} | {info.hint} | {info.sla or ''} | {'да' if status in TERMINAL else ''} |"
        for status, info in STATUS_INFO.items()
    )
    return (
        "# Статусы заявки\n\n"
        "> Файл сгенерирован из `services/core/app/statemachine.py` командой `python -m app.export_docs`. "
        "Руками не править.\n\n"
        "На стрелках — кто выполняет переход: `CLIENT` — клиент, `SYSTEM` — автоматический конвейер, "
        "`MANAGER` / `UNDERWRITER` — сотрудники банка.\n\n"
        f"```mermaid\n{to_mermaid()}\n```\n\n"
        "| Код | Название | Что видит клиент | Обычный срок | Финальный |\n|---|---|---|---|---|\n"
        f"{rows}\n"
    )


def main() -> None:
    contract = REPO / "contracts" / "core.yaml"
    contract.write_text(
        yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
        newline="\n",
    )
    diagram = REPO / "docs" / "architecture" / "statuses.md"
    diagram.parent.mkdir(parents=True, exist_ok=True)
    diagram.write_text(statuses_markdown(), encoding="utf-8", newline="\n")
    print(f"Обновлено: {contract.relative_to(REPO)}, {diagram.relative_to(REPO)}")


if __name__ == "__main__":
    main()
