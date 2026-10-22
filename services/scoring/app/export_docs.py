"""Выгрузка OpenAPI сервиса в contracts/scoring.yaml: python -m app.export_docs"""

from pathlib import Path

import yaml

from app.main import app

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "scoring.yaml"


def main() -> None:
    spec = app.openapi()
    header = "# Сгенерировано из services/scoring (python -m app.export_docs). Руками не править.\n"
    CONTRACT.write_text(header + yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Записано: {CONTRACT}")


if __name__ == "__main__":
    main()
