"""Расчёт платежа (S3.2). Аннуитет: платёж одинаковый каждый месяц, округление до рубля."""


def annuity_payment(amount: float, term_months: int, rate: float) -> int:
    monthly = rate / 12 / 100
    if monthly == 0:
        return round(amount / term_months)
    return round(amount * monthly / (1 - (1 + monthly) ** -term_months))


def payment_schedule(amount: int, term_months: int, rate: float) -> dict:
    payment = annuity_payment(amount, term_months, rate)
    total = payment * term_months
    return {"monthly_payment": payment, "total_payment": total, "overpayment": total - amount}


def max_amount_for_payment(payment: float, term_months: int, rate: float) -> float:
    """Обратная задача: какую сумму можно взять, если платить не больше payment в месяц."""
    if payment <= 0:
        return 0
    monthly = rate / 12 / 100
    if monthly == 0:
        return payment * term_months
    return payment * (1 - (1 + monthly) ** -term_months) / monthly
