# rlt-hack

## Задание

- [Презентация организаторов](task/docs/presentation.pdf)
- [Текстовая транскрипция презентации](task/docs/presentation.md)

## Данные

Исходные данные задачи находятся в `task/data/` и хранятся через Git LFS.
Перед клонированием установите Git LFS. После клонирования выполните `git lfs pull`, если данные не загрузились автоматически.

## Состав решения

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
cp .env.example .env                         # переменные окружения, файл в Git не попадает
docker compose up -d --build                 # фронтенд, ClickHouse с веб-интерфейсом и применение миграций
docker compose run --rm sync-job providers   # подключённые адаптеры источников
docker compose run --rm sync-job sync        # обход включённых источников
```

Фронтенд будет доступен на `http://localhost:8080`, веб-интерфейс ClickHouse —
на `http://localhost:3488`. Вход в интерфейс выполняется пользователем самого
ClickHouse (по умолчанию `default` с пустым паролем); сервис `clickhouse-ui`
обращается к базе сам, из контейнера, поэтому порт 8123 наружу ему не нужен.
Простой встроенный редактор запросов доступен и без него — на
`http://localhost:8123/play`.

Миграции применяются сервисом `migrate` при каждом `up`; повторный запуск
ничего не меняет. Каждый источник включается своим флагом. Каталоги компаний,
YML-фиды и сайты с разметкой schema.org включены и обходятся по sitemap
источника; адаптер исходного CSV выключен, потому что требует выгруженных данных
Git LFS в `task/data` — на рабочем компьютере они не выгружаются.

### Переменные окружения

Все переменные с значениями по умолчанию и пояснениями перечислены в
[.env.example](.env.example): порты и режим фронтенда, образы и доступ к
ClickHouse, адрес для веб-интерфейса, флаги источников и ограничения джобы.
Compose читает их из `.env` в корне проекта и из окружения оболочки; без `.env`
действуют значения по умолчанию, записанные в `docker-compose.yml`. Пустое
значение в `.env` равносильно значению по умолчанию.

Назначение переменных джобы сбора подробнее описано в
[backend/README.md](backend/README.md).
ProductCenter включается флагом `PRODUCTCENTER_WEB_PROVIDER=true` только для
полного обхода: `PRODUCTCENTER_MAX_CARDS=0`. Положительный лимит останавливает
обход без записи неполного снимка.
Успешные страницы ProductCenter хранятся в томе Docker `productcenter-cache`
до 24 часов для продолжения обхода после обрыва сети.
Для живой проверки без записи в ClickHouse используйте команду из
[backend/README.md](backend/README.md); отчёт и кеш размещаются вне Git.

## Применение миграций без Docker

```sh
for file in backend/migration/*.sql; do clickhouse-client --multiquery < "$file"; done
```

Адрес сервера и доступ задаются конфигурацией `clickhouse-client` или его
флагами. Порядок файлов важен. Такой запуск не ведёт учёт применённых
миграций: его ведёт только команда `migrate` из джобы, которая пишет
контрольные суммы в таблицу `supplier_search.schema_migrations`.

## CI/CD

GitHub Actions проверяет frontend, backend и ML на искусственных данных,
собирает контейнеры и после успешного push в `main` разворачивает проверенный
выпуск на сервере. Production использует отдельный Compose-проект, резервную
копию ClickHouse перед миграциями и откат frontend при неуспешном запуске.
Production-конфигурация использует порт 8081 и демонстрационный режим фронтенда,
пока HTTP API не реализован.

Настройка GitHub Secrets, команды эксплуатации и ограничения отката описаны
в [инструкции развёртывания](deploy/README.md).

## Проверки backend

Без сервера ClickHouse, Docker и сети, через `uv`:

```sh
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' python backend/tests/clickhouse/schema_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' --with lxml --with cssselect --with httpx --with openpyxl python backend/tests/supplier/job_smoke.py
uv run --no-project --python 3.13 --with lxml --with cssselect --with httpx python backend/tests/supplier/provider_smoke.py
uv run --no-project --python 3.13 --with lxml --with cssselect --with httpx python backend/tests/supplier/productcenter_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' --with lxml --with cssselect --with httpx python backend/tests/supplier/productcenter_job_smoke.py
uv run --no-project --python 3.13 python backend/tests/supplier/worker_smoke.py
uv run --no-project --python 3.13 --with httpx --with openpyxl python backend/tests/supplier/gisp_registry.py
uv run --no-project --python 3.13 --with httpx --with openpyxl python backend/tests/supplier/gisp_api.py
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

В текущем сравнении выбран Qwen3-Embedding-4B BF16 + BM25/RRF. Отдельный Qwen3-Embedding-8B NF4 прогон был остановлен до завершения индекса; качество не измерялось, поэтому 8B не входит в рабочий pipeline. Зафиксированный частичный запуск указан в [журнале экспериментов](ml/EXPERIMENTS.md).

GPU-проверка запускается через `rlt-gpu-check`. Замеры качества и ресурсов, ограничения метрик и фактические результаты ведутся в [журнале экспериментов](ml/EXPERIMENTS.md).

### Эксперимент с карточками поставщиков

Сборка вариантов A–D выполняется на сервере данных рядом с DuckDB; перед ней
установите актуальный ML-пакет из `/root/rlt/work/ml`. Производные карточки
переносятся на GPU напрямую между серверами. Тексты и выборочные примеры остаются
на серверах.

```bash
cd /root/rlt/work/ml
/root/rlt/.venv312/bin/pip install -e '.[dev]'
PYTHONPATH=src /root/rlt/.venv312/bin/python -m rlt_ml.cards \
  --data /root/rlt/ready-v1 \
  --database /root/rlt/ready-v1/procurement.duckdb \
  --out /root/rlt/runs/card-variants \
  --config configs/supplier_cards.toml
```

На GPU с локальным кешем Qwen3-Embedding-4B выполните аудит токенов:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=src \
  /root/rlt/.venv/bin/python -m rlt_ml.card_audit \
  --variants /root/rlt/data/card-variants \
  --data /root/rlt/data/ready-v1 \
  --model Qwen/Qwen3-Embedding-4B \
  --revision 5cf2132abc99cad020ac570b19d031efec650f2b \
  --out /root/rlt/runs/card-audit
```

Оценка каждого варианта использует один набор validation-запросов, Qwen4B и
замороженные исходные карточки A для BM25; отчёт одного hybrid-прогона содержит
отдельные метрики dense и hybrid. Запуски выполняются последовательно:

```bash
cd /root/rlt/work/ml
for variant in A D; do
  length=256
  [ "$variant" = D ] && length=512
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=src \
    /root/rlt/.venv/bin/python -m rlt_ml.retrieval \
    --data /root/rlt/data/ready-v1 \
    --out "/root/rlt/runs/card-retrieval/$variant" \
    --split validation --model Qwen/Qwen3-Embedding-4B --hybrid \
    --config configs/compare_qwen.toml --batch-size 1 --card-max-length "$length" \
    --cards "/root/rlt/data/card-variants/$variant/cards.parquet" \
    --lexical-cards /root/rlt/data/card-variants/A/cards.parquet \
    --gpu-memory-fraction 0.68 --cpu-threads 2
done
PYTHONPATH=src /root/rlt/.venv/bin/python -m rlt_ml.compare_cards \
  --predictions-dir /root/rlt/runs/card-retrieval \
  --variants AD \
  --out /root/rlt/runs/card-retrieval/paired-comparison.json
```
