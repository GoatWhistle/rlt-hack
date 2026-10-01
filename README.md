# rlt-hack

## Задание

- [Презентация организаторов](task/docs/presentation.pdf)
- [Текстовая транскрипция презентации](task/docs/presentation.md)

## Данные

Исходные данные задачи находятся в `task/data/` и хранятся через Git LFS.
Перед клонированием установите Git LFS. После клонирования выполните `git lfs pull`, если данные не загрузились автоматически.

## Состав решения

- [Источники поставщиков и ассортимента](context/supplier-sources.md)
- [Схема ClickHouse и примеры запросов](context/clickhouse-schema.md)
- [Схема таблиц и всех связей (PDF)](docs/schema-relations.pdf)
- [Миграции ClickHouse](backend/migration)
- [Джоба сбора: контракт источника, адаптеры и команды](backend/README.md)
- [Дизайн-система фронтенда](frontend/DESIGN.md)

Нормализация и HTTP API ещё не реализованы: сейчас в репозитории фронтенд в
демонстрационном режиме, хранилище и джоба сбора данных. Код backend
асинхронный: сервисы сбора готовы к вызову из будущего API на FastAPI.

Для пересборки PDF по миграциям нужен Python, `reportlab==5.0.1` и шрифт
Arial или DejaVu Sans с кириллицей:

```sh
uv run --no-project --with 'reportlab==5.0.1' python docs/generate_schema_pdf.py
```

## Требования

- Node.js 24+
- Python 3.13+ — для джобы сбора и проверок backend
- Docker с Compose v2 — для запуска в контейнерах

## Запуск через Docker Compose

```bash
docker compose up -d --build                 # фронтенд, ClickHouse и применение миграций
docker compose run --rm sync-job providers   # подключённые адаптеры источников
docker compose run --rm sync-job sync        # обход включённых источников
```

Фронтенд будет доступен на `http://localhost:8080`.

Миграции применяются сервисом `migrate` при каждом `up`; повторный запуск
ничего не меняет. Каждый источник включается своим флагом: адаптеры каталогов
выключены, пока их селекторы не сверены с живыми страницами, а адаптер исходного
CSV включён сразу и требует загруженных данных Git LFS.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `WEB_PORT` | `8080` | Порт фронтенда на хосте |
| `VITE_API_BASE_URL` | `/api` | Базовый URL API при сборке |
| `VITE_DEMO_MODE` | `true` | Показывать демонстрационный результат без backend; `false` — отправлять файл в `POST {VITE_API_BASE_URL}/recommendations` |

Переменные окружения хранилища и джобы с значениями по умолчанию:
`CLICKHOUSE_IMAGE`, `CLICKHOUSE_HTTP_PORT` (8123), `CLICKHOUSE_NATIVE_PORT`
(9000), `CLICKHOUSE_USER` (default), `CLICKHOUSE_PASSWORD` (пусто),
`CLICKHOUSE_DATABASE` (supplier_search), `SUPPLIER_DATASET_PROVIDER` (true),
`SYNC_PARALLEL_SOURCES` (4), `SYNC_PARALLEL_REQUESTS` (4),
`SYNC_INTERVAL_SECONDS` (3600), `REQUEST_TIMEOUT` (30), `LOG_LEVEL` (INFO).
Полный список переменных джобы — в [backend/README.md](backend/README.md).

## Применение миграций без Docker

```sh
for file in backend/migration/*.sql; do clickhouse-client --multiquery < "$file"; done
```

Адрес сервера и доступ задаются конфигурацией `clickhouse-client` или его
флагами. Порядок файлов важен. Такой запуск не ведёт учёт применённых
миграций: его ведёт только команда `migrate` из джобы, которая пишет
контрольные суммы в таблицу `supplier_search.schema_migrations`.

## Проверки backend

Без сервера ClickHouse, Docker и сети, через `uv`:

```sh
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' python backend/tests/clickhouse/schema_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' --with lxml --with cssselect --with httpx python backend/tests/supplier/job_smoke.py
uv run --no-project --python 3.13 --with lxml --with cssselect --with httpx python backend/tests/supplier/provider_smoke.py
uv run --no-project --python 3.13 python backend/tests/supplier/worker_smoke.py
```

Проверки используют временные каталоги, встроенный движок chDB и подготовленные
документы вместо сетевых запросов, к рабочей БД не подключаются. Линтер и
форматтер — `ruff`, команды описаны в [backend/README.md](backend/README.md).

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
| `VITE_DEMO_MODE` | `false` отключает демонстрационные данные |

Дизайн-система (цвета, шрифт, отступы, компоненты) описана в [frontend/DESIGN.md](frontend/DESIGN.md).

## ML-пайплайн

Датасет обрабатывается на сервере данных в `/root/rlt`; ZIP и производные таблицы не переносите на рабочий компьютер. Для окружения ML нужен Python 3.12. Все пути ниже показаны для сервера данных, кроме команды оценки на GPU.

```bash
cd /root/rlt/work/ml
python3.12 -m venv /root/rlt/.venv312
/root/rlt/.venv312/bin/pip install -e '.[dev]'
/root/rlt/.venv312/bin/pytest
/root/rlt/.venv312/bin/rlt-prepare \
  --source '/root/rlt/Данные 24-25.zip' \
  --out /root/rlt/ready-v1 \
  --config configs/data.toml
```

Для baseline запустите `rlt-evaluate-retrieval --data /root/rlt/ready-v1 --out /root/rlt/runs/bm25-validation --split validation --model bm25 --config configs/compare_qwen.toml` на подготовленных валидационных данных. На GPU заранее закешируйте открытые веса командой `rlt-cache-models --model Qwen/Qwen3-Embedding-0.6B --model Qwen/Qwen3-Embedding-4B --manifest /root/rlt/runs/models.json`. После этого оценка может идти без сети, задайте `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.

Две сравниваемые модели и общая выборка задаются в `configs/compare_qwen.toml`; для каждого процесса нужен свой `--out`, модели должны видеть один набор `validation` файлов. После передачи производных validation таблиц на GPU перейдите в `/root/rlt/work/ml` и запустите команды в отдельных терминалах:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 rlt-evaluate-retrieval \
  --data /root/rlt/data/ready-v1 --out /root/rlt/runs/qwen-06b \
  --split validation --model Qwen/Qwen3-Embedding-0.6B --hybrid \
  --config configs/compare_qwen.toml --batch-size 4 \
  --gpu-memory-fraction 0.29 --cpu-threads 2

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 rlt-evaluate-retrieval \
  --data /root/rlt/data/ready-v1 --out /root/rlt/runs/qwen-4b \
  --split validation --model Qwen/Qwen3-Embedding-4B --hybrid \
  --config configs/compare_qwen.toml --batch-size 1 \
  --gpu-memory-fraction 0.68 --cpu-threads 2
```

GPU-проверка запускается через `rlt-gpu-check`. Замеры качества и ресурсов, ограничения метрик и фактические результаты ведутся в [журнале экспериментов](ml/EXPERIMENTS.md).
