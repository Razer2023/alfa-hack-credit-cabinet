# GitHub: как устроено и как подключиться

## Как это работает (5 понятий)

- **Репозиторий** — папка проекта с полной историей изменений. Одна копия лежит на GitHub (`origin`), у каждого разработчика своя локальная копия.
- **Коммит** — сохранённый снимок изменений с подписью «кто и что сделал». Коммиты сначала живут только у тебя на компьютере, `git push` отправляет их на GitHub.
- **Ветка** — отдельная линия работы. `main` — общая рабочая версия, в неё никто не пишет напрямую. Каждый делает задачу в своей ветке и не мешает остальным.
- **Pull Request (PR)** — просьба «влей мою ветку в `main`». В PR видно изменения, там же идёт обсуждение, ревью и автоматические проверки (CI). Сливает PR лид.
- **Issue и Projects** — задачи и доска задач внутри GitHub (аналог Trello/Jira).

Цикл одной задачи:
```
main ──●───────────────────────────●── (Squash and merge)
        \                         /
         feat/c-s5.1-scorecard ●──●──●   ← коммиты, push, PR, ревью
```

---

## Часть 1. Настройка репозитория (делает лид, один раз)

### 1.1 Аккаунт и тариф
1. Нужен аккаунт GitHub с включённой двухфакторной аутентификацией (Settings → Password and authentication).
2. **Важно:** правила защиты веток (rulesets) в **приватном** репозитории на бесплатном тарифе работают не всегда. Варианты:
   - **(рекомендуется)** оформить GitHub Student Developer Pack (education.github.com/pack) — студенту он даёт GitHub Pro бесплатно, и защита веток в приватных репозиториях работает;
   - сделать репозиторий публичным (защита работает на любом тарифе), но тогда код видят все.

   После настройки проверь: если в Settings → Rules GitHub пишет, что правила не применяются без апгрейда, значит защиты нет.

### 1.2 Создать репозиторий
1. github.com → **New repository**. Имя, например `alfa-hack-credit-cabinet`, видимость **Private**, без README (он уже есть у нас локально).
2. Залить локальную папку (рекомендуется держать проект **не в OneDrive**: синхронизация OneDrive портит папку `.git`. Например, `C:\dev\alfa-hack`):
   ```bash
   git init -b main
   git config user.name "Razer2023"
   git config user.email "<почта из GitHub>"
   git add .
   git commit -m "Ядро: правила команды и структура репозитория"
   git remote add origin https://github.com/Razer2023/alfa-hack-credit-cabinet.git
   git push -u origin main
   ```

### 1.3 Настройки репозитория (Settings)
- **General → Pull Requests:** оставить только *Allow squash merging*. Выключить merge commits и rebase merging. Включить *Automatically delete head branches*.
- **Rules → Rulesets:** быстрее всего через **New ruleset → Import a ruleset**, по очереди файлы [`.github/rulesets/main-protection.json`](../../.github/rulesets/main-protection.json) и [`release-tags.json`](../../.github/rulesets/release-tags.json). Ниже то же самое для ручной настройки.
- **Rules → Rulesets → New branch ruleset** «main-protection»:
  - Enforcement: Active; Target: Default branch (`main`);
  - ✅ Restrict deletions; ✅ Block force pushes;
  - ✅ Require a pull request before merging → 1 approval, ✅ Require review from Code Owners, ✅ Dismiss stale approvals;
  - ✅ Require status checks to pass: `core-test` и `core-docker` (GitHub Actions). Новые сервисы добавляют свои проверки с уникальными именами (`scoring-test`, `web-build` и т. п.);
  - Bypass list: только Repository admin (лид). Пользоваться обходом лишь в аварийной ситуации.
- **Rules → Rulesets → New tag ruleset** «release-tags»: target `v*`, ✅ Restrict creations, updates, deletions; bypass — Repository admin. Теги версий может ставить только лид.
- **Collaborators → Add people:** пригласить разработчиков (для личного репозитория у них будет роль Write). Для жюри позже добавить аккаунт **`alfa-hack-2026`** (по условиям кейса для приватного репо).
- **Code security:** включить *Secret scanning* и *Push protection*, если доступны. GitHub не даст запушить токен по ошибке.

### 1.4 Метки, доска, задачи
- **Issues → Labels:** `area:A`, `area:B`, `area:C`, `area:D`, `mvp`, `validation`, `not-mvp`, `tz`, `bug`.
- **Projects → New project → Board:** колонки `Todo`, `In progress`, `Review`, `Done`. Привязать к репозиторию.
- Завести Issue на каждую историю из story map (S1.1, S3.1…) с меткой области и приоритета, назначить исполнителя.
- В `.github/CODEOWNERS` заменить `@TODO-…` на реальные GitHub-логины владельцев областей.

---

## Часть 2. Подключение разработчика (каждый, один раз)

1. Принять приглашение (придёт на почту и в уведомления GitHub).
2. Установить **Git for Windows** (git-scm.com). Если удобнее работать мышкой — **GitHub Desktop**, он делает то же самое через кнопки.
3. Представиться Git (имя и почта, как в аккаунте GitHub, иначе коммиты не привяжутся к профилю):
   ```bash
   git config --global user.name "<GitHub-логин>"
   git config --global user.email "<почта из GitHub>"
   ```
4. Авторизация. Самый простой способ — GitHub CLI: установить `gh` (cli.github.com) и выполнить:
   ```bash
   gh auth login
   ```
   (GitHub.com → HTTPS → Login with a web browser). Можно и без него: при первом `git push` Git for Windows сам откроет окно входа через браузер.
5. Склонировать проект в папку **вне OneDrive**:
   ```bash
   git clone https://github.com/Razer2023/alfa-hack-credit-cabinet.git
   ```
6. Прочитать `CONTRIBUTING.md` и `docs/team/AREAS.md`, найти свою область.

---

## Часть 3. Ежедневный цикл (все)

```bash
# 1. Начало задачи: свежий main и новая ветка
git switch main
git pull
git switch -c feat/c-s5.1-scorecard

# 2. Работа: коммитим маленькими шагами
git add services/scoring
git commit -m "Скоринг: S5.1 факторы возраста бизнеса и выручки"

# 3. Перед push: подтянуть изменения
git pull origin main          # влить свежий main в свою ветку
git push -u origin feat/c-s5.1-scorecard   # первый раз; дальше просто git push

# 4. Открыть PR (или кнопкой на сайте)
gh pr create --draft --fill
```

Дальше:
- доводишь задачу, пушишь новые коммиты (PR обновится сам) → **Ready for review** → лид смотрит;
- замечания исправляешь новыми коммитами в ту же ветку;
- после «Squash and merge» начинаешь следующую задачу с шага 1.

### Если `git pull` сообщил о конфликте
Это значит, что ты и кто-то ещё поменяли одни и те же строки. При нашем разделении на области такое бывает редко.
1. `git status` покажет файлы с конфликтом. В них есть блоки `<<<<<<<`, `=======`, `>>>>>>>`.
2. Оставь правильный вариант, удали маркеры.
3. `git add <файл>` → `git commit` → `git push`.
4. Конфликт в чужом файле или ты не уверен — не угадывай, напиши владельцу области или лиду.

### Чего не делать
`git push --force`, `git rebase` запушенной ветки, `git reset --hard` на общих ветках, коммиты в `main` напрямую, коммит файла `.env`.
