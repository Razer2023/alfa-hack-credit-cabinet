"""Синтетические данные встроенных заглушек.

Временная замена сервисов B (данные и интеграции) и C (скоринг), пока они не готовы.
Три демо-компании дают три разных исхода: одобрение, контрпредложение, ручное рассмотрение.
Настоящие данные и правила принадлежат областям B и C (см. docs/team/AREAS.md).
"""

COMPANIES: dict[str, dict] = {
    "7701234567": {
        "name": ("ООО «Кофейня на Лесной»", "EGRUL"),
        "ogrn": ("1207700123456", "EGRUL"),
        "registration_date": ("2020-03-12", "EGRUL"),
        "okved": ("56.10 — Деятельность ресторанов и кафе", "EGRUL"),
        "address": ("г. Москва, ул. Лесная, д. 5", "EGRUL"),
        "director": ("Иванова Мария Сергеевна", "EGRUL"),
        "employees": (12, "FNS"),
        "tax_regime": ("УСН", "FNS"),
        "revenue_year": (24_000_000, "BANK_ACCOUNT"),
        "avg_monthly_turnover": (2_000_000, "BANK_ACCOUNT"),
    },
    "7702345678": {
        "name": ("ООО «СтройМонтаж»", "EGRUL"),
        "ogrn": ("1187700234567", "EGRUL"),
        "registration_date": ("2018-06-01", "EGRUL"),
        "okved": ("43.39 — Работы завершающие и отделочные", "EGRUL"),
        "address": ("г. Москва, Варшавское ш., д. 118", "EGRUL"),
        "director": ("Петров Алексей Викторович", "EGRUL"),
        "employees": (35, "FNS"),
        "tax_regime": ("ОСНО", "FNS"),
        "revenue_year": (30_000_000, "BANK_ACCOUNT"),
        "avg_monthly_turnover": (2_500_000, "BANK_ACCOUNT"),
    },
    "7703456789": {
        "name": ("ООО «Вектор Трейд»", "EGRUL"),
        "ogrn": ("1217700345678", "EGRUL"),
        "registration_date": ("2021-09-20", "EGRUL"),
        "okved": ("46.73 — Торговля оптовая лесоматериалами и стройматериалами", "EGRUL"),
        "address": ("г. Москва, ул. Складочная, д. 1", "EGRUL"),
        "director": ("Сидоров Игорь Павлович", "EGRUL"),
        "employees": (9, "FNS"),
        "tax_regime": ("УСН", "FNS"),
        "revenue_year": (18_000_000, "BANK_ACCOUNT"),
        "avg_monthly_turnover": (1_500_000, "BANK_ACCOUNT"),
    },
}

CREDIT_HISTORY: dict[str, dict] = {
    "7701234567": {"max_overdue_days": 0, "active_loans": 1, "total_debt": 400_000},
    "7702345678": {"max_overdue_days": 0, "active_loans": 2, "total_debt": 3_500_000},
    "7703456789": {"max_overdue_days": 45, "active_loans": 3, "total_debt": 6_000_000},
}

PRODUCTS: list[dict] = [
    {
        "code": "EXPRESS",
        "name": "Экспресс-кредит",
        "description": "Быстрые деньги на текущие задачи без залога",
        "min_amount": 300_000,
        "max_amount": 5_000_000,
        "min_term_months": 3,
        "max_term_months": 24,
        "base_rate": 22.5,
        "purposes": ["Текущие расходы", "Кассовый разрыв", "Закупка"],
    },
    {
        "code": "WORKING_CAPITAL",
        "name": "Кредит на пополнение оборота",
        "description": "Закупка товара, сезонные расходы, кассовые разрывы",
        "min_amount": 1_000_000,
        "max_amount": 30_000_000,
        "min_term_months": 6,
        "max_term_months": 36,
        "base_rate": 19.9,
        "purposes": ["Закупка товара", "Сезонные расходы", "Кассовый разрыв"],
    },
    {
        "code": "INVESTMENT",
        "name": "Инвестиционный кредит",
        "description": "Оборудование, ремонт, открытие новой точки",
        "min_amount": 3_000_000,
        "max_amount": 100_000_000,
        "min_term_months": 12,
        "max_term_months": 84,
        "base_rate": 18.5,
        "purposes": ["Оборудование", "Ремонт", "Новая точка"],
    },
]
