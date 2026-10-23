"""Загрузка и проверка правил из rules/*.yaml.

Правила проверяются при старте сервиса: опечатка в конфиге роняет запуск, а не решение по заявке.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import settings

FACTOR_CODES = (
    "BUSINESS_AGE",
    "REVENUE",
    "BKI_OVERDUE",
    "ACTIVE_LOANS",
    "DEBT_LOAD",
    "LOAN_TO_REVENUE",
    "EMPLOYEES",
    "TAX_DEBT",
    "MASS_ADDRESS",
)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Product(Strict):
    code: str
    name: str
    description: str
    min_amount: int = Field(gt=0)
    max_amount: int = Field(gt=0)
    min_term_months: int = Field(gt=0)
    max_term_months: int = Field(gt=0)
    base_rate: float = Field(gt=0, lt=100)
    purposes: list[str] = []

    @model_validator(mode="after")
    def _ranges(self):
        if self.min_amount > self.max_amount or self.min_term_months > self.max_term_months:
            raise ValueError(f"{self.code}: минимум больше максимума")
        return self


class Catalog(Strict):
    version: str
    products: list[Product] = Field(min_length=1)

    def get(self, code: str) -> Product | None:
        return next((p for p in self.products if p.code == code), None)


class Bin(Strict):
    lt: float | None = None
    points: int


class Factor(Strict):
    title: str
    unit: Literal["years", "rub", "days", "count", "share", "flag"]
    bins: list[Bin] = Field(min_length=1)

    @model_validator(mode="after")
    def _bins_sorted(self):
        bounds = [b.lt for b in self.bins[:-1]]
        if None in bounds or bounds != sorted(bounds) or self.bins[-1].lt is not None:
            raise ValueError("корзины должны идти по возрастанию lt, последняя — без lt")
        return self

    def points(self, value: float) -> int:
        for b in self.bins:
            if b.lt is None or value < b.lt:
                return b.points
        raise AssertionError("последняя корзина без lt ловит всё")


class RiskClass(Strict):
    code: str
    min_score: int
    decision: Literal["AUTO", "MANUAL_REVIEW", "REJECT"]
    limit_share: float | None = Field(None, gt=0, le=1)
    rate_adjustment: float = 0.0

    @model_validator(mode="after")
    def _auto_has_limit(self):
        if self.decision == "AUTO" and self.limit_share is None:
            raise ValueError(f"класс {self.code}: для AUTO нужен limit_share")
        return self


class StopFactors(Strict):
    min_business_age_months: int
    max_overdue_days: int
    egrul_ok_statuses: list[str]


class ManualReview(Strict):
    overdue_days_from: int
    tax_debt_above: int
    mass_address: bool


class Affordability(Strict):
    free_cash_flow_share: float = Field(gt=0, le=1)
    existing_debt_monthly_share: float = Field(ge=0, le=1)
    min_dscr: float = Field(gt=0)
    amount_step: int = Field(gt=0)
    term_step: int = Field(gt=0)


class ManualOffer(Strict):
    fallback_limit_share: float = Field(gt=0, le=1)


OFFER_CHECK_CODES = (
    "AMOUNT_BELOW_PRODUCT",
    "AMOUNT_OVER_PRODUCT",
    "TERM_OUT_OF_PRODUCT",
    "RATE_BELOW_MIN",
    "AMOUNT_OVER_LIMIT",
    "DSCR_TOO_LOW",
    "NO_FINANCIAL_DATA",
)


class Scorecard(Strict):
    version: str
    base_score: int
    factors: dict[str, Factor]
    risk_classes: list[RiskClass] = Field(min_length=1)
    stop_factors: StopFactors
    manual_review: ManualReview
    affordability: Affordability
    manual_offer: ManualOffer
    offer_checks: dict[str, str]
    reasons: dict[str, str]

    @model_validator(mode="after")
    def _consistent(self):
        missing = set(FACTOR_CODES) - set(self.factors)
        if missing:
            raise ValueError(f"нет факторов: {sorted(missing)}")
        scores = [c.min_score for c in self.risk_classes]
        if scores != sorted(scores, reverse=True) or scores[-1] != 0:
            raise ValueError("классы риска — по убыванию min_score, последний с min_score: 0")
        missing_checks = set(OFFER_CHECK_CODES) - set(self.offer_checks)
        if missing_checks:
            raise ValueError(f"нет текстов offer_checks: {sorted(missing_checks)}")
        return self

    @property
    def best_rate_adjustment(self) -> float:
        return min(c.rate_adjustment for c in self.risk_classes)

    def offer_check(self, code: str, level: str = "error", **params) -> dict:
        return {"code": code, "level": level, "text": self.offer_checks[code].format(**params)}

    def risk_class(self, score: int) -> RiskClass:
        return next(c for c in self.risk_classes if score >= c.min_score)

    def reason(self, code: str, **params) -> dict:
        return {"code": code, "text": self.reasons[code].format(**params)}


class Rules(Strict):
    catalog: Catalog
    scorecard: Scorecard

    @property
    def model_version(self) -> str:
        return f"{self.scorecard.version}+{self.catalog.version}"


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_rules(rules_dir: Path) -> Rules:
    return Rules(
        catalog=Catalog.model_validate(_read(rules_dir / "products.yaml")),
        scorecard=Scorecard.model_validate(_read(rules_dir / "scorecard.yaml")),
    )


@lru_cache
def get_rules() -> Rules:
    return load_rules(settings.rules_dir)
