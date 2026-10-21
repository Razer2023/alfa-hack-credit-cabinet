# Веб-интерфейс (область D)

React 18 + TypeScript + Vite на дизайн-системе Альфа-Банка `@alfalab/core-components@50.37.0`, тема `corp`. Правила оформления — в [docs/design/DESIGN.md](../docs/design/DESIGN.md).

## Разработка
Нужен Node.js 22 (не ниже 20.19).

```bash
cd web
npm ci
npm run dev        # http://localhost:5173, /api проксируется на ядро http://localhost:8000
npm run lint
npm run build
```

Ядро на другом адресе: `CORE_URL=http://localhost:8080 npm run dev`.

## Docker
Образ собирает статику и раздаёт её через nginx (порт 80). Запросы `/api/` nginx проксирует на `core:8000`, поток событий `/api/v1/stream` — без буферизации ([nginx.conf](nginx.conf)).

## Тема и стили
- `src/index.css` подключает токены `vars/bundle/corp.css` и тему компонентов `themes/corp.css`.
- Цвета и отступы — только токены: `--color-light-*`, `--gap-<px>` (`--gap-16`, `--gap-24` …). Именованные `--gap-m`, `--gap-l` и часть цветов в библиотеке помечены устаревшими, их не используем.
- Миксины типографики (`@mixin headline_small` и т. п.) обрабатывает `postcss-mixins`, чтобы использовать их в CSS-модуле, импортируйте `@alfalab/core-components/vars/typography.css` в начале файла.
- Шрифт системный: фирменные шрифты банка не подключаются.
