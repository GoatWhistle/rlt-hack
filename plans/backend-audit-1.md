# Аудит backend 1: безопасность и надёжность

Охват — пункты 1 «Безопасность» и 6 «Надёжность и асинхронность» из [audits.md](audits.md#аудиты-backend). Ветка `feature/supplier-search-api`, 2026-10-02. Проверяемый код: `backend/src/controller/{api,http,search,supplier,upload,health}`, `backend/src/application/{api,config,deferred_gateway}.py`, `backend/src/service/{supplier_search,procurement_upload,supplier_profile,health}`, `backend/src/adapter/{repository/clickhouse/*,client/ml_service,file/notice_csv}`, миграции `0007`–`0009`, `backend/Dockerfile`, `docker-compose.yml`, `deploy/{compose.production.yml,nginx.conf,release.sh,package.sh,production.env.example}`, `contracts/`.

## Как проверяли

- Чтение кода по чек-листу: SQL и параметры, лимиты входа, ошибки и логи, заголовки, ML-клиент, пул ClickHouse, фоновая обработка загрузок, жизненный цикл, сборка и развёртывание.
- `uv run python -m pytest` в `backend/` на Windows: 350 тестов прошли, тесты chDB пропущены (chDB на Windows недоступен).
- `pip-audit` по окружению проекта и по `uv export --frozen --no-dev` из `uv.lock` (92 пакета): известных уязвимостей нет. Ключевые версии: fastapi 0.142.2, starlette 1.7.0, uvicorn 0.54.0, python-multipart 0.0.32, httpx 0.28.1, clickhouse-connect 1.9.0, pydantic 2.13.5.
- Временные скрипты против настоящих классов приложения с фейками вместо ClickHouse лежат вне репозитория: `%TEMP%/claude/w--Projects-hacks-rlt-hack/1d28b4c7-…/scratchpad/backend-audit1/`:
  - `ch_down.py` — `build_app()` с недоступным ClickHouse (`127.0.0.1:1`) через `httpx.ASGITransport`;
  - `pool_timeout.py` — удержание слотов `GatewayPool` после таймаута;
  - `starvation.py` — общий пул для загрузок и поиска;
  - `runner_save.py` — сбой сохранения результата закупки;
  - `wide_csv.py`, `wide_rss.py`, `wide_lag.py` — память, время и задержка цикла при разборе CSV;
  - `amplification.py` — число SQL-запросов на один поиск;
  - `inject.py` — формулы в названиях позиций и ссылка `javascript:` в контактах;
  - `inputs.py` — лимиты входа на фейковых сервисах.
- Замеры выполнены локально на Python 3.14 (интерпретатор uv); в образе Python 3.13. Живой ClickHouse и Docker не запускались: время тяжёлых запросов на реальном объёме не измерено.

Код не менялся.

## Резюме

Основа безопасная: весь пользовательский текст уходит в ClickHouse только параметрами `{name:Type}`, ответы об ошибках не раскрывают внутренности, в логах нет текста запроса, ML-клиент не доверяет ответу, частичные отказы каналов, обогащения и архива дают предупреждения, а не 500. API стартует без ClickHouse и восстанавливается без перезапуска.

Слабые места — устойчивость к нагрузке и злоупотреблениям на публичном адресе:

- Один анонимный CSV на 10 МБ с широкой шапкой занимает ≈1,26 ГБ памяти. У контейнера API нет лимита памяти, на хосте рядом работает ClickHouse.
- Таймаут поиска не отменяет запросы в ClickHouse. Слоты пула заняты, пока запрос не закончится сам, вплоть до 300 с. Один поиск порождает до 100 SQL-запросов, ограничений частоты нет.
- Фоновые загрузки делят с интерактивным поиском один пул из 4 клиентов. Под загрузкой поиск замедляется в 10–13 раз.
- Закупка, результат которой не удалось сохранить, навсегда остаётся «в очереди» до перезапуска.
- При недоступном ClickHouse все маршруты, кроме `POST /api/searches`, отвечают `500 internal_error` вместо 503.
- Продакшн-образ API собирается без `--target` и работает от root. `/api/docs` открыт в продакшне и подгружает Swagger UI с CDN без SRI.

Находок: **P0 — 1, P1 — 10, P2 — 12**.

## Находки

### P0 — блокирует релиз

#### 1. Широкая шапка CSV занимает ≈1,3 ГБ памяти на один запрос

- Где: `backend/src/adapter/file/notice_csv/table.py:20-38` (`detect_delimiter` делит всю первую строку на три списка, `read_records` материализует все ячейки), `backend/src/adapter/file/notice_csv/reader.py:23-36` (`header` ещё раз копирует ячейки), `deploy/compose.production.yml:2-6` (у `api` нет `mem_limit`).
- Воспроизведение: файл `lot_id;procedure_name` и ещё 10 485 730 символов `;`, затем строка `L1;x`, всего 10,5 МБ. Это меньше `UPLOAD_MAX_BYTES` и лимита nginx 12 МБ. `wide_rss.py`: пиковый RSS **+1262 МБ**. `wide_lag.py`: разбор в `to_thread` идёт 2,7 с, задержка событийного цикла из-за GIL до **820 мс**. Файл принимается (`lots=1`). Три параллельных запроса дают ≈4 ГБ, а ClickHouse ограничен `CLICKHOUSE_MEMORY_LIMIT=1500m` на том же хосте.
- Исправление:
  - До разбора отклонять файл, если первая строка длиннее разумного предела (например, 64 КБ) или в шапке больше `MAX_COLUMNS` (например, 64). Код `invalid_file` или новый `too_many_columns`.
  - Снизить `csv.field_size_limit` до 32 КБ.
  - Читать записи потоком и прерываться на `max_rows + 2`, не материализуя весь файл.
  - Ограничить число одновременных разборов семафором 1–2.
  - Задать `api` в `compose.production.yml` `mem_limit` (например, 768m) и `pids_limit`.
- Тест: `tests/adapter/file/test_notice_csv_limits.py::test_rejects_header_wider_than_limit` — шапка из 1 млн разделителей даёт `UnreadableNoticeFileError` быстрее 0,2 с. `::test_peak_memory_is_bounded` — пик `tracemalloc` на 10 МБ входа меньше 64 МБ.

### P1 — исправить до фронтенд-аудитов

#### 2. Таймаут поиска не освобождает ClickHouse: слоты пула заняты до 300 с

- Где:
  - `backend/src/adapter/repository/clickhouse/pool/gateway.py:51-56`: `asyncio.shield` возвращает клиента в пул только после завершения потока.
  - `gateway.py:57-60`: `asyncio.to_thread` не прерывается.
  - `client.py:33,42-46`: `send_receive_timeout=query_timeout`; в настройках сессии нет `max_execution_time` и `max_result_rows`.
  - `config.py:15`: `query_timeout=300` — общий для джобы и API.
  - `service/supplier_search/service.py:42-47`.
  - Усилитель — `adapter/text/rule_interpreter/interpreter.py:14` (`MAX_ITEMS=50`), а `offer_search/retriever.py:43` и `history_search/retriever.py:47` отправляют по запросу на позицию параллельно.
- Воспроизведение:
  - `amplification.py`: текст из 50 позиций (2 тыс. символов) даёт **100 SELECT** на один поиск, обогащение ещё не считали.
  - `pool_timeout.py`: пул на 4 клиента, «тяжёлые» запросы по 3 с, поиск с таймаутом 0,5 с получил `timeout`. Следующий дешёвый запрос ждал слот **2,5 с**, а `/api/health/ready` в это время отвечает `ready=false`: проба идёт через тот же пул.
  - На реальном объёме несколько таких поисков подряд держат API недоступным, пока ClickHouse сам не закончит запросы.
- Исправление:
  - Для пула API передавать настройки `max_execution_time` ≈ `SEARCH_TIMEOUT_SECONDS + 2`, `timeout_overflow_mode='throw'`, `max_result_rows`/`result_overflow_mode='break'`, `max_memory_usage`. `send_receive_timeout` для API — отдельная переменная, например 15 с, у джобы остаётся 300.
  - При отмене лиза выполнять `KILL QUERY WHERE query_id = …`: передавать свой `query_id` в `client.query`.
  - Снизить `MAX_ITEMS` для интерактивного поиска или объединять позиции канала в один запрос.
  - Пробу готовности выполнять отдельным клиентом вне пула.
- Тест:
  - `tests/adapter/repository/clickhouse/test_pool.py::test_cancelled_lease_kills_running_query` — фейк записывает `KILL QUERY` с тем же `query_id`.
  - `tests/application/test_api.py::test_api_client_limits_execution_time` — настройки клиента API содержат `max_execution_time`.
  - `tests/service/health/test_health.py::test_probe_does_not_wait_for_busy_pool`.

#### 3. Фоновые загрузки и интерактивный поиск делят один пул

- Где: `backend/src/application/api.py:47` (один `DeferredGateway`), `:136-140` (`ClickHouseUploadStore` и `LotProcessor` с `self.matcher()` на том же шлюзе). Вместе с `service/procurement_upload/runner.py:37-41` и `UPLOAD_CONCURRENCY=4` (`application/config.py:82`) на 4 слота `CLICKHOUSE_POOL_SIZE` (`config.py:186`) это значит, что каждая закупка — полный поиск до 50 позиций.
- Воспроизведение: `starvation.py` с настоящим `GatewayPool(4)` и запросом 50 мс. Поиск без нагрузки — 0,10 с, на фоне четырёх закупок по 10 позиций — **1,08–1,32 с**, в 11–13 раз дольше. Когда запросы идут 0,5–0,7 с, поиск выходит за `SEARCH_TIMEOUT_SECONDS=8` и отвечает 504. Закупки тоже упираются в `UPLOAD_LOT_TIMEOUT_SECONDS`, повторяются трижды (находка 17) и ещё сильнее нагружают пул.
- Исправление: дать загрузкам отдельный пул на 1–2 клиента (или семафор на их долю слотов) и держать `UPLOAD_CONCURRENCY` меньше доли пула. Ещё вариант — приоритетная очередь лизов, где поиск обслуживается раньше закупок.
- Тест: `tests/application/test_api.py::test_uploads_use_separate_gateway`. `tests/adapter/repository/clickhouse/test_pool.py::test_interactive_lease_not_starved_by_background` — p95 ожидания интерактивного лиза под фоновой нагрузкой ограничен.

#### 4. Нет ограничения частоты и очереди для `POST /api/searches` и `POST /api/uploads`

- Где: `deploy/nginx.conf:25-60` — нет `limit_req`/`limit_conn`. `backend/src/service/procurement_upload/runner.py:26`: неограниченная `asyncio.Queue()`. `service.py:51-66`: каждая загрузка добавляет до 5000 закупок без проверки очереди. В uvicorn нет `--limit-concurrency`.
- Воспроизведение: по коду. Анонимный клиент шлёт N загрузок по 5000 строк. Все закупки держатся в памяти процесса (до 10 МБ текста на загрузку) и обрабатываются по 4 штуки. При худшем раскладе одна загрузка занимает API на часы (см. находку 17). Каждый `POST /api/searches` даёт до 100 SQL (находка 2).
- Исправление:
  - nginx: `limit_req_zone $binary_remote_addr zone=search:10m rate=2r/s` для `POST /api/searches` (через `map $request_method`), `limit_req … burst=10 nodelay`, `limit_conn` до 1 на IP для `/api/uploads`, `limit_req_status 429`.
  - Сервис: общий предел очереди закупок. Сверх него `UploadQueueFullError` → `429 upload_queue_full` с `Retry-After`.
  - Поиск: семафор одновременных поисков с быстрым `503 search_busy`.
- Тест: `tests/service/procurement_upload/test_service.py::test_rejects_upload_when_backlog_is_full`, `tests/controller/test_upload_api.py::test_queue_full_maps_to_429`. Шаг в `deploy/smoke.sh`: серия из 30 поисков получает хотя бы один 429.

#### 5. Закупка навсегда остаётся «в очереди», если результат не сохранился

- Где: `backend/src/service/procurement_upload/runner.py:96-109` — после `attempts` неудачных `save_result` метод молча возвращается. `:58-69`: `_resume` читает незавершённые закупки только при старте. `:76-78`: ключ снимается с `_known`.
- Воспроизведение: `runner_save.py` с `MemoryUploadStore(failing_saves=3)` и `attempts=3`. Через секунду после `drain()`: `saved results: 0`, статус закупки `queued`, `pending: 1`, раннер работает. Пользователь видит вечный прогресс, пока API не перезапустят. Финальная ошибка даже не пишется уровнем `error`.
- Исправление: продолжать попытки сохранения с экспоненциальной паузой до успеха (ключ остаётся в `_known`) или периодически повторять `_resume` (каждые `resume_interval`) для закупок вне `_known`. На последней неудаче писать `logger.error` с `upload_id` и `lot_id`.
- Тест: `tests/service/procurement_upload/test_runner.py::test_lot_is_saved_after_store_recovers` — `failing_saves = attempts`, затем хранилище восстанавливается, и результат появляется без перезапуска.

#### 6. Недоступный ClickHouse даёт `500 internal_error` почти на всех маршрутах

- Где: `backend/src/controller/http/errors.py:76-87,95-96,153-154`. `RepositoryUnavailableError` (`adapter/repository/errors.py`) не классифицируется и попадает в `handle_unexpected`. Для 503 есть только `SearchUnavailableError`, когда отказали все каналы.
- Воспроизведение: `ch_down.py`. Старт 0,0 с, `/live` 200, `/ready` 503 за 2 с, `POST /api/searches` → 503 `search_unavailable`. Но `GET /api/searches`, `GET /api/searches/{id}`, `GET /api/suppliers/{id}`, `GET /api/uploads`, `POST /api/uploads` → **500 `internal_error`**, каждый с полным стектрейсом в логе уровня `ERROR`. Фронтенд не отличает «хранилище недоступно, повторите» от дефекта.
- Исправление: объявить ошибку недоступности хранилища на уровне сервиса (например, `StorageUnavailableError` в `service/errors.py`) и переводить в неё `RepositoryUnavailableError` на границе адаптера или сервиса. Обработчик возвращает `503 storage_unavailable` и `Retry-After`. Код добавить в таблицу ошибок `backend/README.md`, в `ERRORS` роутеров и в `contracts/*/error.example.json`.
- Тест: `tests/controller/test_errors.py::test_storage_outage_maps_to_503` для каждого маршрута на фейковом сервисе. `tests/application/test_api_e2e.py::test_unreachable_clickhouse_returns_503`.

#### 7. Продакшн-образ API работает от root

- Где: `deploy/package.sh:12-13` — `docker build` без `--target`, поэтому собирается последняя стадия `job` (`backend/Dockerfile:34-37`) без `USER`. `deploy/compose.production.yml:3` запускает этот образ как `api`. Непривилегированный `USER api` (`Dockerfile:26-28`) есть только в стадии `api`, а её используют лишь локальный Compose и README.
- Воспроизведение: по коду и правилам Docker. Без `--target` собирается последняя стадия. Проверка на сервере: `docker compose exec api id -u` выдаёт `0`.
- Исправление: собирать два образа (`--target api` → `rlt/backend-api`, `--target job` → `rlt/backend-job`) или перенести `useradd`/`USER` в стадию `base`. Для `api` в `compose.production.yml` добавить `read_only: true`, `tmpfs: /tmp`, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`.
- Тест: в `deploy/smoke.sh` после активации — `test "$(compose exec -T api id -u)" != 0`.

#### 8. Документация API открыта в продакшне и грузит скрипты с CDN без SRI

- Где: `docker-compose.yml:185` (`API_DOCS: ${API_DOCS:-true}`), `deploy/production.env.example` (переменной нет), `backend/src/application/config.py:58,102`, `backend/src/controller/http/app.py:44-46`. nginx проксирует весь `/api/`. FastAPI отдаёт Swagger UI со скриптом `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js`: плавающая мажорная версия, без `integrity`, на том же origin, что и SPA.
- Воспроизведение: `inputs.py` — `GET /api/openapi.json` с настройками по умолчанию отвечает 200. В продакшне по этой же цепочке `/api/docs` доступен по `https://rlt.goatwhistle.ru/api/docs`. Подмена пакета на CDN даёт выполнение чужого кода на origin приложения.
- Исправление: `API_DOCS: ${API_DOCS:-false}` в `compose.production.yml`, `API_DOCS=false` в `production.env.example`, при необходимости `location ^~ /api/docs { return 404; }`. Если документация нужна снаружи — раздавать ассеты Swagger UI локально.
- Тест: `deploy/smoke.sh` — `curl -s -o /dev/null -w '%{http_code}' …/api/openapi.json` равен 404.

#### 9. `contacts.site` не проверяется: в API проходят `javascript:`, относительные и `//host`

- Где: `backend/src/controller/search/mapper.py:74-79` (`site=supplier.website` как есть); значения приходят из парсеров (`adapter/supplier/pulscen_web/parsing.py:104` — атрибут `data-to`, `gisp_registry/workbook.py:147`, `moscow_suppliers/provider.py:134`). Фронтенд выводит `<a href={site}>` (`frontend/src/entities/evidence/ui/contact-list/index.tsx:16`). В контракте (`contracts/search/response.example.json:96`) — абсолютный `https://…` или пустая строка.
- Воспроизведение: `inject.py` — `Supplier(website="javascript:alert(document.cookie)")` → `{'site': 'javascript:alert(document.cookie)', …}`. XSS сейчас гасит React 19.3: в `react-dom` есть блокировка `javascript:`. Но значение без схемы (`www.example.ru`) становится относительной ссылкой внутри приложения, а `//evil.example` — внешним переходом. Ссылки оснований (`models/evidence.py`) проверяются, контакты нет.
- Исправление: в `contacts_dto` отдавать `site` только при `is_web_url(...)`, иначе `""`. При сборе нормализовать адрес без схемы до `https://`. `email` проверять простым шаблоном.
- Тест: `tests/controller/test_search_api.py::test_contacts_site_keeps_only_web_urls`, параметризованный значениями `javascript:alert(1)`, `//evil.example`, `www.example.ru`, `https://ok.example`. Аналогичный тест для профиля поставщика.

#### 10. CSV-инъекция в выгрузке результатов

- Где: `frontend/src/features/export-results/csv.ts:40-43`. `cell()` кавычит только `",;\n\r` и не нейтрализует ведущие `=`, `+`, `-`, `@`, `\t`, `\r`. Значения приходят из backend: названия позиций из `procedure_name`/`subject` загруженного CSV и названия поставщиков из обходов внешних сайтов.
- Воспроизведение: `inject.py` — `RuleQueryInterpreter` сохраняет `=HYPERLINK("http://evil.example","бумага`, `@SUM(1+1)*cmd|' /C calc'!A0 бумага`, `+бумага офисная` как названия позиций. После выгрузки `products.csv`/`suppliers.csv` Excel исполняет формулу.
- Исправление: в `cell()` добавлять `'` перед строками, начинающимися с `= + - @ \t \r`, кроме числовых колонок. Правка во фронтенде, отдельной задачей после текущих фронтенд-правок.
- Тест: `frontend/tests/features/export-results/csv.test.ts` — `toCsv` экранирует каждое из шести начал и не трогает числа.

#### 11. Оценка зависимостей не совпадает с тем, что попадает в образ

- Где: `backend/Dockerfile:13-16` — `pip install uv` без версии, `uv pip install --system -r pyproject.toml` ставит последние версии по нижним границам и игнорирует `uv.lock`. Базовый `python:3.13-slim` без дайджеста.
- Воспроизведение: по коду. `pip-audit` по `uv.lock` чистый, но в образ попадают другие версии, разрешённые в момент сборки; повторная сборка того же коммита может дать другой набор.
- Исправление: `COPY pyproject.toml uv.lock ./` и `uv sync --frozen --no-dev --no-install-project`, версия uv из `ghcr.io/astral-sh/uv:<версия>`, базовый образ по дайджесту. В CI шаг `uv export --frozen | pip-audit -r /dev/stdin`.
- Тест: шаг CI `pip-audit` по `uv.lock`; проверка, что `pip freeze` в образе совпадает с `uv export --frozen`.

### P2 — бэклог

#### 12. Не все входные поля ограничены

- Где:
  - `backend/src/controller/search/dto.py:27`: `regions: list[str]` без предела числа и длины.
  - `backend/src/controller/upload/dto.py:129`: элементы `lot_ids` без предела длины.
  - `backend/src/controller/upload/router.py:77-83`: `lot_id` в пути не проверяется по `LOT_ID_PATTERN` до запроса в БД.
  - В приложении нет предела тела запроса; локальный Compose публикует `8000` на `0.0.0.0`.
- Воспроизведение: `inputs.py`. 1000 регионов по 1000 символов → 201, все 1000 доходят до сервиса и уходят параметром в ClickHouse. JSON на 20 МБ разбирается целиком, ответ 422 `query_too_long`. Элемент `lotIds` на 100 тыс. символов → 404 после запроса в БД. В продакшне тело режет nginx (1 МБ).
- Исправление: `regions: list[Annotated[str, StringConstraints(max_length=100)]] = Field(max_length=20)`, `lot_ids: list[Annotated[str, StringConstraints(max_length=64, pattern=…)]]`. Неверный `lot_id` в пути → 404 без запроса. ASGI-ограничение тела 64 КБ для JSON.
- Тест: `tests/controller/test_search_api.py::test_rejects_too_many_regions`, `tests/controller/test_upload_api.py::test_rejects_long_lot_ids`, `::test_malformed_lot_id_does_not_reach_store`.

#### 13. Ответ 404 повторяет произвольный сегмент пути

- Где: `backend/src/controller/search/mapper.py:43-47`, `controller/supplier/mapper.py:11-15`, `controller/upload/mapper.py:42-46`, `service/errors.py:37-40,43-46,53-56` — сообщение строится из сырого значения.
- Воспроизведение: `inputs.py`: `GET /api/searches/xxx…` (300 символов) → `message` длиной 317 с этими символами. JSON экранируется, но это отражённый пользовательский ввод.
- Исправление: при неверном формате id — постоянное сообщение (`"search not found"`), без исходного значения.
- Тест: `tests/controller/test_errors.py::test_not_found_message_does_not_echo_input`.

#### 14. Заголовки nginx неполные

- Где: `deploy/nginx.conf:16-18,62-73`. Нет `Content-Security-Policy` и `Strict-Transport-Security` (`deploy/Caddyfile` тоже их не ставит), `server_tokens` включён. `add_header` в `location /assets/` и `location = /index.html` отменяет наследование, поэтому там теряется `Referrer-Policy`.
- Воспроизведение: по конфигурации и правилам наследования `add_header` в nginx; `curl -I /index.html` покажет отсутствие `Referrer-Policy`.
- Исправление: `server_tokens off;`. Общий набор заголовков через `include` во всех `location` с `add_header`. CSP `default-src 'self'; frame-ancestors 'none'; base-uri 'self'` (сверить с фронтендом). HSTS — в Caddy.
- Тест: `deploy/smoke.sh` — `curl -sI` на `/`, `/index.html`, `/assets/…`, `/api/health/live` проверяет все заголовки.

#### 15. API ходит в ClickHouse администратором

- Где: `docker-compose.yml:24` (`CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT: 1`), `:63-69,182` (у `api` те же `CLICKHOUSE_USER`/`PASSWORD`, что у `migrate`).
- Воспроизведение: по конфигурации. Пользователь API может выполнять DDL и управлять доступом.
- Исправление: отдельный пользователь API — `SELECT` на читаемые таблицы, `INSERT` в `searches`, `uploads`, `upload_lots`, `upload_results`, профиль с `max_execution_time` и `max_memory_usage` (дополняет находку 2).
- Тест: шаг smoke — `INSERT INTO supplier_search.offers` от пользователя API завершается ошибкой доступа.

#### 16. `--forwarded-allow-ips "*"`

- Где: `docker-compose.yml:180`.
- Воспроизведение: по конфигурации. Любой клиент, достучавшийся до `api` напрямую (локально порт 8000 на `0.0.0.0`), подменяет `X-Forwarded-For` и `-Proto`. Сейчас IP клиента нигде не используется, но станет важен для ограничения частоты в приложении.
- Исправление: доверять только подсети Compose или держать ограничение частоты только в nginx.
- Тест: не требуется, достаточно проверки конфигурации в review.

#### 17. Закупки повторяются при любой ошибке, включая таймаут и детерминированные

- Где: `backend/src/service/procurement_upload/runner.py:81-94`.
- Воспроизведение: по коду. `TimeoutError` от `asyncio.timeout(30)` и ошибки разбора данных повторяются `attempts=3` раза. Худший случай — 3×30 + 3 с на закупку, при 5000 закупках и 4 обработчиках ≈ 32 ч. Под перегрузкой повторы усиливают её (находка 3).
- Исправление: повторять только транзиентные ошибки (недоступность хранилища; таймаут не больше одного раза), детерминированные сразу помечать `failed`, к паузе добавить случайный разброс.
- Тест: `tests/service/procurement_upload/test_runner.py::test_deterministic_error_is_not_retried`.

#### 18. Повторная загрузка того же файла дублирует обработку

- Где: `backend/src/service/procurement_upload/service.py:51-66`.
- Воспроизведение: по коду. Повтор `POST /api/uploads` после сетевого сбоя создаёт новую загрузку с новым UUID и заново ставит все закупки в очередь.
- Исправление: заголовок `Idempotency-Key` или хеш содержимого с окном дедупликации; при совпадении возвращать существующую загрузку.
- Тест: `tests/service/procurement_upload/test_service.py::test_same_idempotency_key_returns_existing_upload`.

#### 19. Сохранение архива входит в бюджет таймаута поиска

- Где: `backend/src/service/supplier_search/service.py:42-47,82-89`.
- Воспроизведение: по коду. Если вставка в архив затянулась до конца `SEARCH_TIMEOUT_SECONDS`, пользователь получает 504 при готовом результате. Защищённая `shield` вставка в пуле всё равно завершается и сохраняет поиск, которого пользователь не видел.
- Исправление: отдельный короткий таймаут на `archive.save`; при его срабатывании ответ 201 с предупреждением `archiveFailed`.
- Тест: `tests/service/supplier_search/test_service.py::test_slow_archive_returns_result_with_warning`.

#### 20. Фоновая обработка рассчитана на один процесс

- Где: `backend/src/service/procurement_upload/runner.py:26-27,58-69` — очередь в памяти и разовая дообработка при старте.
- Воспроизведение: по коду. При `--workers N` или нескольких репликах каждый процесс поднимает все незавершённые закупки и обрабатывает их параллельно.
- Исправление: зафиксировать в `backend/README.md` и Compose один процесс API или ввести аренду закупки (`claimed_by`, `claimed_until`).
- Тест: архитектурная проверка, что команда запуска API не содержит `--workers`.

#### 21. Списки поисков и загрузок открыты всем

- Где: `backend/src/controller/search/router.py:58-64`, `controller/upload/router.py:44-49`.
- Воспроизведение: по коду. Аутентификации нет, `GET /api/searches` отдаёт тексты чужих запросов, `GET /api/uploads` — имена файлов и закупки. В логах при этом хранится только хеш запроса.
- Исправление: продуктовое решение. Либо задокументировать, что инструмент однопользовательский, либо привязать списки к сессии или токену.
- Тест: после решения — тест, что чужие поиски не попадают в `recent`.

#### 22. ML-клиент не ограничивает размер ответа

- Где: `backend/src/adapter/client/ml_service/retriever.py:78,85`, `dto.py:115` (`candidates` без предела).
- Воспроизведение: по коду. Ответ читается целиком, все ИНН из него уходят одним массивом в `ids_by_inn`.
- Исправление: отбрасывать ответ больше N КБ (потоковое чтение с пределом), обрезать кандидатов до `limit × k` до запроса в ClickHouse, `trust_env=False` для внутреннего адреса.
- Тест: `tests/adapter/client/test_ml_service.py::test_oversized_response_is_rejected`, `::test_candidates_are_capped_before_identity_lookup`.

#### 23. Загрузка может оставить строки закупок без загрузки

- Где: `backend/src/adapter/repository/clickhouse/upload_store/store.py:58-61` — сначала `upload_lots`, потом `uploads`.
- Воспроизведение: по коду. Если вторая вставка упала, клиент получает 500, а строки `upload_lots` остаются в таблице. Они не видны (`SELECT_PENDING` фильтрует по `uploads_current`), но копятся.
- Исправление: TTL на сиротские строки или периодическая очистка; порядок вставки сохранить.
- Тест: `tests/clickhouse/…::test_orphan_lots_are_not_resumed` (Linux, chDB).

## Что уже хорошо

- **SQL.** Пользовательский текст, токены и id идут только параметрами `{name:Type}`, включая `multiSearchAny`/`multiSearchAllPositions`. Через `format` подставляются лишь имя БД из окружения и статичные фрагменты. Иглы ограничены: 64 на позицию, 255 в истории участий.
- **Лимиты входа.** DTO запроса строгие (`extra="forbid"`, `strict=True`). Текст до 4000 символов после схлопывания пробелов, `limit` 1..50, `recent` до 50, `lotIds` до 5000, позиций до 50.
- **Заголовки и id.** `X-Request-Id` принимается только по `[A-Za-z0-9-]{8,64}`. `Accept-Language` разбирается устойчиво. Неверный UUID в пути даёт 404, а не 500.
- **Ошибки и логи.** Для 500 наружу уходит только `internal error` и `requestId`, стектрейс — в JSON-лог. В логах поиска — длина и SHA-256 текста, в логах загрузки — размер файла. CORS не включён.
- **Основания.** Ссылки оснований — только абсолютные `http(s)` (`models/evidence.py`), иначе основание не строится.
- **Загрузка CSV:**
  - проверка `Content-Length` до чтения;
  - `max_files=1`, `max_fields=8`, `read(limit + 1)`;
  - сигнатуры ZIP/OLE/PDF и `NUL` в начале → 415;
  - предел строк, шаблон и уникальность `lot_id`;
  - имя файла обрезается до базового и 255 символов;
  - разбор вынесен в поток.
- **ML-клиент.** Фиксированный `base_url`, таймауты. Повторы только при транспортной ошибке и 503. Проверяются мажорная `schemaVersion` и эхо `requestId`. `matchedItemIds` фильтруются по известным позициям, редиректы выключены.
- **Частичные отказы.** Сбой канала, источника обогащения или архива даёт предупреждение. Только отказ всех каналов → 503, таймаут → 504.
- **Отказ ClickHouse и восстановление.** API стартует без ClickHouse (ленивый `DeferredGateway` и пул), `/ready` честно отвечает 503. Неудачное открытие клиента возвращает слот, после подъёма ClickHouse всё работает без перезапуска (`ch_down.py`).
- **Жизненный цикл.** `lifespan` останавливает раннер, закрывает ML-клиент и пулы. Незавершённые закупки дообрабатываются при старте, отменённые остаются незавершёнными и подхватываются снова.
- **Развёртывание:**
  - порты ClickHouse и API в продакшне — только localhost;
  - секреты в окружении, `production.env` с правами `0640`;
  - `release.sh` проверяет ревизию, номер запуска и имя БД регуляркой, сверяет контрольные суммы и делает резервную копию перед миграциями;
  - у nginx пределы тела 1 и 12 МБ и таймауты прокси.
- **Зависимости.** `pip-audit` по `uv.lock` и окружению — без известных уязвимостей.

## Ограничения проверки

- Время тяжёлых запросов ClickHouse на реальном объёме не измерялось: chDB на Windows недоступен, живой ClickHouse не поднимался. Насколько серьёзна находка 2 на настоящих данных, решит нагрузочный замер из пункта 2 чек-листа.
- Docker не запускался. Находки 7, 8 и 14 подтверждены по конфигурации и правилам Docker и nginx, а не запуском образа.
- Замеры памяти и времени разбора CSV сделаны на Windows и Python 3.14, в образе Linux и Python 3.13. Порядок величин сохранится.
