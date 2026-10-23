"""Конфиг правил: битый файл не должен пройти проверку."""

import shutil

import pytest
import yaml
from pydantic import ValidationError

from app.rules import load_rules


@pytest.fixture
def rules_dir(tmp_path):
    from app.config import settings

    shutil.copytree(settings.rules_dir, tmp_path, dirs_exist_ok=True)
    return tmp_path


def edit(path, change):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_shipped_rules_valid(rules_dir):
    assert load_rules(rules_dir).model_version == "scorecard-1.1+products-1.0"


def test_unsorted_bins_rejected(rules_dir):
    edit(rules_dir / "scorecard.yaml", lambda d: d["factors"]["REVENUE"]["bins"].reverse())
    with pytest.raises(ValidationError):
        load_rules(rules_dir)


def test_missing_factor_rejected(rules_dir):
    edit(rules_dir / "scorecard.yaml", lambda d: d["factors"].pop("DEBT_LOAD"))
    with pytest.raises(ValidationError):
        load_rules(rules_dir)


def test_product_min_over_max_rejected(rules_dir):
    edit(rules_dir / "products.yaml", lambda d: d["products"][0].update(min_amount=10**9))
    with pytest.raises(ValidationError):
        load_rules(rules_dir)
