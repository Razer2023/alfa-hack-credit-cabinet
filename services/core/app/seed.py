"""Демо-компании и тестовые учётные записи. Запуск: python -m app.seed (повторный запуск ничего не дублирует).

Пароль у всех демо-пользователей один — CORE_DEMO_PASSWORD (см. .env.example).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Company, Role, User
from app.security import hash_password

COMPANIES = [
    ("7701234567", "ООО «Кофейня на Лесной»"),
    ("7702345678", "ООО «СтройМонтаж»"),
    ("7703456789", "ООО «Вектор Трейд»"),
]

# Контакты сотрудников банка, которые клиент видит в заявке (S4.9). Телефоны вымышленные.
STAFF_CONTACTS = {
    "manager": ("Кредитный менеджер малого бизнеса", "+7 495 000-00-01", "пн–пт 9:00–19:00"),
    "underwriter": ("Кредитный специалист", "+7 495 000-00-02", "пн–пт 10:00–18:00"),
}

# login, ФИО, роль, ИНН компании
USERS = [
    ("coffee", "Иванова Мария Сергеевна", Role.CLIENT, "7701234567"),
    ("stroy", "Петров Алексей Викторович", Role.CLIENT, "7702345678"),
    ("vector", "Сидоров Игорь Павлович", Role.CLIENT, "7703456789"),
    ("manager", "Смирнова Ольга Андреевна", Role.MANAGER, None),
    ("underwriter", "Кузнецов Дмитрий Игоревич", Role.UNDERWRITER, None),
]


def seed(session: Session) -> None:
    companies = {c.inn: c for c in session.scalars(select(Company))}
    for inn, name in COMPANIES:
        if inn not in companies:
            companies[inn] = Company(inn=inn, name=name)
            session.add(companies[inn])
    session.flush()

    existing = {u.login: u for u in session.scalars(select(User))}
    for login, full_name, role, inn in USERS:
        if login not in existing:
            existing[login] = User(
                login=login,
                full_name=full_name,
                role=role,
                company_id=companies[inn].id if inn else None,
                password_hash=hash_password(settings.demo_password),
            )
            session.add(existing[login])
        if login in STAFF_CONTACTS and existing[login].phone is None:
            existing[login].position, existing[login].phone, existing[login].work_hours = STAFF_CONTACTS[login]
    session.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
    print("Демо-данные загружены")
