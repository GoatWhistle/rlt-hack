# rlt-hack

## Задание

- [Презентация организаторов](task/docs/presentation.pdf)
- [Текстовая транскрипция презентации](task/docs/presentation.md)

## Данные

Исходные данные задачи находятся в `task/data/` и хранятся через Git LFS.
Перед клонированием установите Git LFS. После клонирования выполните `git lfs pull`, если данные не загрузились автоматически.

## Состав решения

- [Схема таблиц и всех связей (PDF)](docs/schema-relations.pdf)
- [Идея нормализатора и классификатора](context/normalization-and-classification.md) ([PDF](docs/normalization-and-classification.pdf))
- [Миграции ClickHouse](backend/migration)
- [Справочники ОКПД2, рубрик, словаря и ОКЕИ](backend/reference)
- [Джоба сбора: контракт источника, адаптеры и команды](backend/README.md)
- [Дизайн-система фронтенда](frontend/DESIGN.md)

Добавлены HTTP API на FastAPI и поиск по историческим профилям поставщиков.
Фронтенд использует только HTTP-ответы; демонстрационные карточки удалены.

Нормализация и классификация подключены к джобе сбора через интерфейсы и
вызываются сразу после обхода источника: сначала приведение позиции к единой
форме, затем код ОКПД2, рубрика и тип. Классификатор не угадывает — позиция без
сработавшего канала остаётся без кода, и это видно в отчёте о покрытии. Правила
и замысел описаны в [отдельном документе](context/normalization-and-classification.md).

Для пересборки PDF нужен Python, `reportlab==5.0.1` и шрифт Arial или
DejaVu Sans с кириллицей. Первая команда рисует схему по миграциям, вторая
собирает PDF из описания нормализатора в `context/`:

```sh
uv run --no-project --with 'reportlab==5.0.1' python docs/generate_schema_pdf.py
uv run --no-project --with 'reportlab==5.0.1' python docs/generate_normalization_pdf.py
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
docker compose run --rm sync-job normalize   # пересчёт нормализации и классификации
docker compose run --rm sync-job coverage    # отчёт о покрытии
docker compose run --rm sync-job reidentify  # перевод позиций на новое правило ключа
docker compose run --rm sync-job registry-import  # реестр МСП ФНС для ролей компаний
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
потоковый обход до записи. Товары сохраняются порциями до 32 записей ещё во
время обхода; снятие отсутствующих товаров с продажи выполняется только после
его полного успешного завершения. Эмбеддер читает новые и изменённые предложения
из ClickHouse: батч `EMBEDDING_BATCH_SIZE=16`, ожидание неполного батча
`EMBEDDING_BATCH_WAIT_SECONDS=5` секунд. Векторы записываются одним INSERT
на батч. После ошибки незаписанный батч остаётся доступным для повторной обработки.
Успешные страницы ProductCenter хранятся в томе Docker `productcenter-cache`
до 48 часов для продолжения обхода после обрыва сети. По умолчанию адаптер
делает один запрос за раз с интервалом не меньше секунды и ждёт восстановления
соединения при временном отказе; настройки описаны в backend README.
Для живой проверки без записи в ClickHouse используйте команду из
[backend/README.md](backend/README.md); отчёт и кеш размещаются вне Git.

Там же приведены команды полного браузерного экспорта ГИСП и его загрузки
из локального снимка в ClickHouse. Для экспорта нужен Google Chrome и `npm ci`
в `backend/`; файлы снимка хранятся вне Git.

## Применение миграций без Docker

```sh
for file in backend/migration/*.sql; do clickhouse-client --multiquery < "$file"; done
```

Адрес сервера и доступ задаются конфигурацией `clickhouse-client` или его
флагами. Порядок файлов важен. Такой запуск не ведёт учёт применённых
миграций: его ведёт только команда `migrate` из джобы, которая пишет
контрольные суммы в таблицу `supplier_search.schema_migrations`.

## CI/CD

Запуск парсера и локального эмбеддера, ограничения ресурсов и команды поиска:
[воркеры и векторизация](deploy/WORKERS.md).

GitHub Actions проверяет frontend, backend и ML на искусственных данных,
собирает контейнеры и после успешного push в `main` разворачивает проверенный
выпуск на сервере. Production использует отдельный Compose-проект, резервную
копию ClickHouse перед миграциями и откат frontend при неуспешном запуске.
Production-конфигурация использует frontend на порту 8081 и search-api
на внутреннем порту 8080; запросы `/api/` проксируются к search-api.

Настройка GitHub Secrets, команды эксплуатации и ограничения отката описаны
в [инструкции развёртывания](deploy/README.md).

## Проверки backend

Без сервера ClickHouse, Docker и сети, через `uv`:

```sh
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' python backend/tests/clickhouse/schema_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' python backend/tests/clickhouse/normalization_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' --with lxml --with cssselect --with httpx --with openpyxl python backend/tests/supplier/job_smoke.py
uv run --no-project --python 3.13 --with lxml --with cssselect --with httpx python backend/tests/supplier/provider_smoke.py
uv run --no-project --python 3.13 --with lxml --with cssselect --with httpx python backend/tests/supplier/productcenter_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' --with lxml --with cssselect --with httpx python backend/tests/supplier/productcenter_job_smoke.py
uv run --no-project --python 3.13 --with httpx python backend/tests/supplier/moscow_suppliers_smoke.py
uv run --no-project --python 3.13 python backend/tests/supplier/worker_smoke.py
uv run --no-project --python 3.13 --with httpx --with openpyxl python backend/tests/supplier/gisp_registry.py
uv run --no-project --python 3.13 --with httpx --with openpyxl python backend/tests/supplier/gisp_api.py
uv run --no-project --python 3.13 python backend/tests/supplier/enrich_smoke.py
uv run --no-project --python 3.13 python backend/tests/supplier/identity_smoke.py
uv run --no-project --python 3.13 python backend/tests/supplier/reidentify_smoke.py
uv run --no-project --python 3.13 python backend/tests/normalizer/normalizer_smoke.py
uv run --no-project --python 3.13 python backend/tests/classifier/classifier_smoke.py
uv run --no-project --python 3.13 --with lxml python backend/tests/registry/registry_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' python backend/tests/registry/registry_store_smoke.py
uv run --no-project --python 3.13 --with httpx --with openpyxl python backend/tests/supplier/gisp_snapshot.py
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

Для оценки CatBoost поверх готового retrieval-пула используйте только validation
прогнозы и модель, обученную на train. Команда строит признаки по validation-ТРУ
и считает метрики с пропуском победителя, если его нет в пуле; это oracle-режим
для upstream предсказания ТРУ:

```bash
cd /root/rlt/work/ml
PYTHONPATH=src /root/rlt/.venv312/bin/python -m rlt_ml.candidate_ranker \
  --data /root/rlt/ready-v1 \
  --predictions /root/rlt/backups/embedding-results/run-20261001/qwen-4b/predictions.jsonl \
  --model /root/rlt/runs/ranker-20261001-b/ranker.cbm \
  --out /root/rlt/runs/full-chain-ranker-validation
```

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
# Проверка поиска поставщиков

Тестовый файл: [`test-supplier-search.csv`](test-supplier-search.csv), пять
искусственных закупок. Откройте https://rlt.goatwhistle.ru/, загрузите CSV,
откройте результат закупки. Поиск использует исторические профили по ИНН;
актуальный ассортимент, названия компаний и контакты требуют проверки.

Тестовый HTTP режим принимает до 20 закупок и 2 МБ в одном CSV. Результаты
сохраняются на сервере и доступны в том же браузере (cookie сессии).
Прямой запрос: `POST /api/suppliers/search` с JSON
`{"query":"Поставка офисной бумаги А4","limit":10}`.
Проверка API: `GET /api/health`.

Для локального запуска готовый индекс монтируется через `SUPPLIER_INDEX_PATH`
(каталог с `card_vectors.npy`, `cards.parquet`, `report.json`, `manifest.json`),
затем `docker compose --profile search --profile ml up -d search-api embedder`.
Модель должна быть заранее загружена в кеш. API слушает `127.0.0.1:18082`.
Проверки на искусственном индексе: `cd backend && uv run python tests/search/smoke.py`.


Прогресс ProductCenter сохраняется в `crawl-progress.json` внутри постоянного
тома `productcenter-cache`. Подтверждение порции записывается после успешного
INSERT; после перезапуска незавершённая порция повторяется, подтверждённые
карточки пропускаются. До завершения обхода сохраняется его исходная отметка
времени. Не удаляйте этот том при обычном обновлении сервисов.

### Архивные основания рекомендаций

При `RLT_RUN_SEARCH=true` CD импортирует основания для текущего индекса перед запуском
API. `RLT_HISTORY_DIR` (по умолчанию `/root/rlt/ready-v1`) содержит read-only
`procurement.duckdb`; граница истории берётся из manifest индекса (2024-12-01 для validation,
2025-06-01 для test).
В ClickHouse сохраняются до пяти закупок на поставщика и категорию, точное число
закупок и однозначных побед. Повторный запуск проверяет полноту и не дублирует данные.
Ссылки в карточке открывают архивную запись в пределах сессии загрузки.
Результат процедуры не трактуется как подтверждение исполнения или текущего наличия.

Ранжировщик подключается автоматически, если рядом с индексом есть
`ranker/runtime.json`, `ranker.cbm` и снимки статистики. Перед загрузкой проверяются
хеши, список признаков и соответствие карточкам; без артефакта работает гибридный
поиск. Артефакт экспортируется только после положительной оценки на закрытом test:

```bash
python -m rlt_ml.reranking.candidates --data /data/ready --vectors /data/vectors --out /data/candidates --split train --customer-dropout 0.5
python -m rlt_ml.reranking.train --train /data/train-candidates --validation /data/validation-candidates --text-validation /data/validation-text-candidates --out /data/models
python -m rlt_ml.reranking.evaluate --models /data/models --candidates /data/test-candidates --out /data/models/test-report.json
python -m rlt_ml.reranking.export --models /data/models --vectors /data/validation-vectors --data /data/ready --out /data/release-index
```

Команды выполняются на сервере в окружении `ml`. В Git входят только код и
агрегированные результаты; данные, векторы и веса остаются вне репозитория.

## Качество рекомендаций

RANK-004: 4000 train-запросов, отдельный validation из 1000 запросов; только
Qwen3-Embedding-4B, гибридный поиск top-200 и CatBoost на кандидатах поиска.
Фактические товары целевого лота не используются как вход. Таблица — режим
**только по тексту**, без ИНН заказчика и цены, как в тестовом CSV сайта.

| Метрика validation | Гибридный поиск | Выбранный ранжировщик |
| --- | ---: | ---: |
| MRR исторического победителя | 0.2036 | 0.2577 |
| Победитель на первом месте | 13.72% | 17.89% |
| Известный участник в top-10 | 39.30% | 48.90% |
| Recall участников в top-10 | 31.96% | 39.80% |

Победитель отсутствующего retrieval-пула считается промахом. Участие в закупке —
неполная разметка релевантности, а не доказательство исполнения или наличия товара.
Шкала модели не выдаётся за вероятность победы. Выбор сделан на validation;
закрытый test ещё рассчитывается. [Полный отчёт](ml/reports/ranker-v2-validation.json)
и [журнал экспериментов](ml/EXPERIMENTS.md) содержат сравнение всех трёх вариантов.
