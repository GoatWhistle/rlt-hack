# Запуск и проверки

## Требования

- Node.js 24+
- Python 3.13+ — для джобы сбора и проверок backend
- Docker с Compose v2 — для запуска в контейнерах

## Запуск через Docker Compose

```bash
cp .env.example .env                         # переменные окружения, файл в Git не попадает
docker compose up -d --build                 # фронтенд, API, ClickHouse с веб-интерфейсом и применение миграций
docker compose run --rm sync-job providers   # подключённые адаптеры источников
docker compose run --rm sync-job sync        # обход включённых источников
docker compose run --rm sync-job normalize   # пересчёт нормализации и классификации
docker compose run --rm sync-job coverage    # отчёт о покрытии
docker compose run --rm sync-job reidentify  # перевод позиций на новое правило ключа
docker compose run --rm sync-job registry-import  # реестр МСП ФНС для ролей компаний
```

Фронтенд будет доступен на `http://localhost:8080`, HTTP API — на
`http://localhost:8000/api` (документация — `http://localhost:8000/api/docs`,
через фронтенд — `http://localhost:8080/api/`), веб-интерфейс ClickHouse —
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

### Приоритет региона

В форме поиска можно выбрать регион поставки. Компании с совпадающим регионом
регистрации из реестра МСП получают небольшой бонус; другие регионы и компании
без сведений остаются в пуле. Регистрация не подтверждает географию доставки.
В CSV используйте необязательную колонку `delivery_region` с двухзначным кодом
региона, например `78`. Без региона дополнительный бонус не применяется.

После миграции `0016` уже загруженный реестр нужно перечитать для заполнения
регионов: `docker compose run --rm sync-job registry-import`.

### Переменные окружения

Все переменные с значениями по умолчанию и пояснениями перечислены в
[.env.example](../.env.example): порты и режим фронтенда, образы и доступ к
ClickHouse, адрес для веб-интерфейса, флаги источников и ограничения джобы.
Compose читает их из `.env` в корне проекта и из окружения оболочки; без `.env`
действуют значения по умолчанию, записанные в `docker-compose.yml`. Пустое
значение в `.env` равносильно значению по умолчанию.

Назначение переменных API, поиска и джобы сбора подробнее описано в
[backend/README.md](backend.md).
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
[backend/README.md](backend.md); отчёт и кеш размещаются вне Git.

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

## CI

Запуск парсера и локального эмбеддера, ограничения ресурсов и команды поиска:
[воркеры и векторизация](workers.md).

GitHub Actions (`.github/workflows/ci.yml`) на каждый push в `main` и pull request
проверяет frontend, backend и ML на искусственных данных.

## Проверки backend

Тесты, линтер и типы из `backend/`: `uv run pytest`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run mypy`. Полный прогон в Linux, включая
тесты с chDB: `docker compose --profile tests run --rm backend-tests`.

Smoke-проверки без сервера ClickHouse, Docker и сети, через `uv`:

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
форматтер — `ruff`, команды описаны в [backend/README.md](backend.md).

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

Цвета, шрифты, отступы и движение заданы токенами в `frontend/src/shared/styles/tokens/`.

