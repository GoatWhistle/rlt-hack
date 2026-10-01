# rlt-hack

## Задание

- [Презентация организаторов](task/docs/presentation.pdf)
- [Текстовая транскрипция презентации](task/docs/presentation.md)

## Данные

Исходные данные задачи находятся в `task/data/` и хранятся через Git LFS.
Перед клонированием установите Git LFS. После клонирования выполните `git lfs pull`, если данные не загрузились автоматически.

## Требования

- Node.js 24+
- Docker с Compose v2 — для запуска в контейнерах

## Запуск через Docker Compose

```bash
docker compose up --build
```

Фронтенд будет доступен на `http://localhost:8080`.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `WEB_PORT` | `8080` | Порт фронтенда на хосте |
| `VITE_API_BASE_URL` | `/api` | Базовый URL API при сборке |

## Frontend

```bash
cd frontend
npm ci --silent
cp .env.example .env.local
npm run dev
```

| Команда | Что делает |
| --- | --- |
| `npm run dev` | Dev-сервер на `http://localhost:5173` |
| `npm run build` | Проверка типов и production-сборка в `dist/` |
| `npm run rules` | Правила репозитория: длина файлов, комментарии, CSS, i18n |
| `npm run lint` / `npm run format` | Biome: проверка / автоисправление |
| `npm run typecheck` | TypeScript |
| `npm test` | Unit- и компонентные тесты |
| `npm run test:coverage` | Тесты с порогом покрытия 80 % |
| `npm run e2e` | Playwright + axe; перед первым запуском выполните `npx playwright install chromium` |
| `npm run verify` | Всё, кроме e2e; должно проходить перед сдачей |

Переменные окружения фронтенда (`frontend/.env.local`):

| Переменная | Назначение |
| --- | --- |
| `VITE_API_BASE_URL` | Базовый URL API, по умолчанию `/api` |
| `VITE_API_PROXY` | Адрес backend для прокси `/api` в dev-режиме |
