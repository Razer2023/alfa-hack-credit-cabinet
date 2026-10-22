"""Сквозная проверка: три демо-сценария через API ядра на настоящих сервисах B и C.

Запуск после `docker compose up`:
    cd services/core && uv run python ../../deploy/e2e/scenarios.py http://localhost:8080/api/v1
Пароль демо-пользователей берётся из CORE_DEMO_PASSWORD (как в .env).
"""

import os
import sys
import time

import httpx

sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/api/v1"
PASSWORD = os.environ.get("CORE_DEMO_PASSWORD", "demo")
c = httpx.Client(base_url=BASE, timeout=15)
ok = True


def login(name):
    r = c.post("/auth/login", json={"login": name, "password": PASSWORD})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def wait(h, path, statuses, timeout=30):
    for _ in range(timeout * 2):
        app = c.get(path, headers=h).json()
        if app["status"]["code"] in statuses:
            return app
        time.sleep(0.5)
    raise AssertionError(f"{path}: застряла в {app['status']['code']}")


def submit(h, inn, product, amount, term):
    app = c.post("/applications", json={"product_code": product}, headers=h).json()
    p = f"/applications/{app['id']}"
    c.patch(p, json={"amount": amount, "term_months": term, "purpose": "Пополнение оборота"}, headers=h).raise_for_status()
    r = c.post(f"{p}/prefill", json={"inn": inn}, headers=h)
    r.raise_for_status()
    sources = {f["source"] for f in r.json()["form"]["company"].values()}
    code = c.post(f"{p}/submit/code", headers=h).json()
    c.post(f"{p}/submit/confirm", json={"confirmation_id": code["confirmation_id"], "code": code["demo_code"]}, headers=h).raise_for_status()
    return p, sources


def sign(h, p):
    code = c.post(f"{p}/sign/code", headers=h).json()
    r = c.post(f"{p}/sign/confirm", json={"confirmation_id": code["confirmation_id"], "code": code["demo_code"]}, headers=h)
    r.raise_for_status()


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"  {'OK ' if cond else 'FAIL'} {name} {detail}")


uw = login("underwriter")

print("1) coffee: одобрение -> подпись -> выдача")
h = login("coffee")
p, sources = submit(h, "7701234567", "EXPRESS", 2_000_000, 12)
check("профиль из интеграций", sources == {"EGRUL", "FNS", "BANK_ACCOUNT"}, str(sorted(sources)))
app = wait(h, p, {"APPROVED", "COUNTER_OFFER", "REJECTED", "MANUAL_REVIEW", "NEED_INFO"})
card = c.get(p.replace("/applications", "/bank/applications"), headers=uw).json()
check("решение настоящего скоринга", card["scoring"]["model_version"].startswith("scorecard"), card["scoring"]["model_version"])
check("статус APPROVED", app["status"]["code"] == "APPROVED", f"{app['status']['code']} score={card['scoring'].get('score')}")
sign(h, p)
app = wait(h, p, {"ISSUED"})
check("ISSUED", app["status"]["code"] == "ISSUED", app["offers"][0]["amount"])

print("2) stroy: контрпредложение -> принять -> подпись -> выдача")
h = login("stroy")
p, _ = submit(h, "7702345678", "WORKING_CAPITAL", 10_000_000, 12)
app = wait(h, p, {"APPROVED", "COUNTER_OFFER", "REJECTED", "MANUAL_REVIEW", "NEED_INFO"})
check("статус COUNTER_OFFER", app["status"]["code"] == "COUNTER_OFFER", app["status"]["code"])
offer = app["offers"][0]
print(f"     предложение: {offer['amount']:,} руб. на {offer['term_months']} мес., ставка {offer['rate']}, платёж {offer['monthly_payment']:,}")
print(f"     причины: {[r['text'] for r in app['decision']['reasons']]}")
c.post(f"{p}/offers/{offer['id']}/accept", headers=h).raise_for_status()
sign(h, p)
app = wait(h, p, {"ISSUED"})
check("ISSUED", app["status"]["code"] == "ISSUED")

print("3) vector: ручное рассмотрение -> запрос данных -> дополнение -> отказ")
h = login("vector")
p, _ = submit(h, "7703456789", "WORKING_CAPITAL", 3_000_000, 12)
app = wait(h, p, {"APPROVED", "COUNTER_OFFER", "REJECTED", "MANUAL_REVIEW", "NEED_INFO"})
check("статус MANUAL_REVIEW", app["status"]["code"] == "MANUAL_REVIEW", app["status"]["code"])
bp = p.replace("/applications", "/bank/applications")
card = c.post(f"{bp}/take", headers=uw).json()
check("БКИ из интеграций: просрочка 45 дн.", card["enrichment"]["bki"]["max_overdue_days"] == 45, card["enrichment"]["bki"])
print(f"     факторы скоринга: {[(f['code'], f.get('impact')) for f in card['scoring']['factors']][:5]}")
c.post(f"{bp}/info-request", json={"items": [{"field": "overdue_explanation", "message": "Поясните просрочку"}]}, headers=uw).raise_for_status()
wait(h, p, {"NEED_INFO"})
c.post(f"{p}/info", json={"extra": {"overdue_explanation": "Задержка оплаты от заказчика"}}, headers=h).raise_for_status()
app = wait(h, p, {"MANUAL_REVIEW", "APPROVED", "COUNTER_OFFER", "REJECTED"})
check("снова MANUAL_REVIEW", app["status"]["code"] == "MANUAL_REVIEW", app["status"]["code"])
c.post(f"{bp}/decision", json={"result": "REJECT", "comment": "Высокая долговая нагрузка"}, headers=uw).raise_for_status()
app = c.get(p, headers=h).json()
check("REJECTED с причиной", app["status"]["code"] == "REJECTED", app["decision"]["reasons"][0]["text"])

print("ИТОГ:", "все сценарии прошли" if ok else "ЕСТЬ ОШИБКИ")
sys.exit(0 if ok else 1)
