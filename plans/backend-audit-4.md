# Аудит backend 4: API и контракт, наблюдаемость, тесты

Охват — пункты 8 «API и контракт», 9 «Наблюдаемость» и 10 «Тесты» из [audits.md](audits.md#аудиты-backend). Ветка `feature/supplier-search-api`, база проверки — `561629f`, 2026-10-02. Пока шёл аудит, в ветку вошли исправления по [backend-audit-1.md](backend-audit-1.md) (HEAD `60d95d3`). Все находки повторно проверены на `60d95d3`: у каждой отмечено, сохраняется ли она. Темы аудита 1 (пулы, лимиты, таймауты, 503 при недоступном ClickHouse, Docker, контакты) здесь не повторяются.

Проверяемый код: `backend/src/controller/{http,search,supplier,upload,health,api}`, `backend/src/service/{supplier_search,procurement_upload,health}`, `backend/src/adapter/repository/clickhouse/search_archive`, `backend/src/adapter/client/ml_service`, `backend/tests/`, `contracts/`, `frontend/src/entities/{search,upload,recommendation,supplier,evidence}/parse.ts`, `frontend/src/shared/api/`, `.github/workflows/ci-cd.yml`, `deploy/smoke.sh`, `docker-compose.yml`, `backend/Dockerfile`.

## Как проверяли

- `uv run python -m pytest` в `backend/` на Windows:
  - `561629f`: 350 прошли, 7 модулей с chDB пропущены;
  - `60d95d3`: 432 прошли, те же 7 пропущены.
- `pytest --cov=src`: покрытие 83,4 % на `561629f` и 85,3 % на `60d95d3`. Порог `fail_under = 90` из `pyproject.toml` не достигнут.
- Временные скрипты лежат вне репозитория: `%TEMP%/claude/w--Projects-hacks-rlt-hack/1d28b4c7-…/scratchpad/backend-audit4/`. Они запускались против снимков `git archive` обеих ревизий:
  - `openapi_probe.py` — выгрузка и разбор OpenAPI;
  - `behavior_probe.py` — коды, заголовки, кэширование, корреляция логов на настоящем `create_app` с фейковыми сервисами и настоящим `ChannelRunner`;
  - `domain_error_probe.py` — как отображаются нарушения инвариантов домена;
  - `reraise_probe.py` и запуск `uvicorn … --factory` с недоступным ClickHouse — что попадает в журнал при 500;
  - `detail_size.py` — размер и время сериализации детали загрузки на 5000 закупок;
  - `enum_compare.py` — сверка перечислений backend с константами фронтенда;
  - `mutate.py` — ручная мутационная выборка: 23 мутанта политики, ранжирования и мапперов, полный прогон тестов на каждом;
  - `fuzz.py` — случайные тексты для `RuleQueryInterpreter` (4000 запусков) и заголовки `Accept-Language` (3000 запусков);
  - смоук-скрипты, которых нет в CI: `classifier_smoke`, `normalizer_smoke`, `enrich_smoke`, `identity_smoke`, `reidentify_smoke`, `pulscen_smoke`. Все проходят при `PYTHONUTF8=1`.
- Примеры `contracts/*.json` прогнаны через DTO. Это делают и существующие тесты: `tests/controller/test_contracts.py`, `test_upload_api.py`, а во фронтенде `tests/entities/{search,supplier,upload}`.

Код не менялся.

## Резюме

Контракт между backend и фронтендом сейчас согласован:

- все 16 перечислений ответа совпадают с константами фронтенда;
- каждый пример `contracts/` проходит DTO туда и обратно и разбирается парсерами фронтенда;
- инварианты моделей (ранги, связи совпадений с позициями, оценки в 0..1) гарантируют то, что фронтенд проверяет при разборе.

Тесты в основном проверяют поведение. Правила политики, RRF и подсветки ловят все мутации выборки.

Слабые места — эксплуатация и защита от регрессий:

- **Ошибки.** Нарушение инварианта домена на стороне сервера отвечает `422 invalid_request` и пишется в лог уровнем `INFO` без стека. Дефект выглядит как ошибка клиента.
- **Логи.** Ответы 500 не попадают в журнал запросов и не получают `Server-Timing`. Под uvicorn CLI (Compose и образ) трассировка дублируется многострочным текстом не в JSON: один запрос дал 263 строки лога, из них 9 в JSON.
- **Корреляция и метрики.** `requestId` не доходит до логов сервиса, ML-сервиса и ClickHouse. Метрик нет совсем, нет и итогового события поиска.
- **Опрос загрузок.** Фронтенд раз в секунду запрашивает деталь загрузки целиком: 1,64 МБ и 48 мс сериализации в событийном цикле на 5000 закупок, без `ETag` и пагинации.
- **Сквозные проверки.** Ни одна проверка не выполняет успешный поиск через настоящий ClickHouse. Релиз принимается по `/api/health/live`. Пропуск chDB-тестов не валит CI, порог покрытия не проверяется.
- **OpenAPI.** Описание неточное: у загрузки нет тела, у профиля 422 описан чужой схемой, общие для роутера статусы, ни одного примера.

Находок: **P0 — 0, P1 — 7, P2 — 10**.

## Статус исправлений

Проверено: `ruff check`, `ruff format --check`, `mypy`, `pytest` на Windows и в Linux-контейнере с chDB и `REQUIRE_CHDB=1` (покрытие 97,95 % при пороге 90), смоуки chDB, `shellcheck deploy/smoke.sh`, засев и сценарий смоука на chDB, `npm run verify`, `npm run e2e`, `docker compose config` для обычного и продакшн-набора. Сам `deploy/smoke.sh` с образами не запускался.

| № | Приоритет | Статус | Что сделано |
| --- | --- | --- | --- |
| 1 | P1 | закрыта | на 422 только `InvalidInputError`; нарушения инвариантов — 500 `internal_error`, ERROR со стеком; `test_server_side_invariant_violation_is_internal` |
| 2 | P1 | закрыта | `RequestContextMiddleware` — самый внешний слой приложения: ловит исключение, отдаёт 500 с `X-Request-Id` и `Server-Timing`, пишет одну запись `request completed`; uvicorn запускается с `--log-config src/controller/api/logging.json` (Compose и `Dockerfile`) |
| 3 | P1 | закрыта | `contextvars` + `RequestIdFilter`; `X-Request-Id` в ML-сервис, `log_comment` в ClickHouse; канал, источник и `search_id` полями |
| 4 | P1 | закрыта | событие `search completed`; `/api/metrics` (Prometheus, закрыт в nginx): HTTP по маршрутам, кандидаты по статусам, пустые поиски, предупреждения |
| 5 | P1 | закрыта | слабый `ETag` по прогрессу и 304 без чтения закупок; `GET /api/uploads/{id}/summary`; фронтенд опрашивает сводку раз в секунду, деталь — раз в 5 с и после окончания. Постраничная выдача закупок не делалась: фильтр и поиск по закупкам выполняются на клиенте |
| 6 | P1 | закрыта | смоук: `ready`, засев компании и предложения, поиск → 201, переход по `Location`, профиль, загрузка CSV до `processed == total` без `failed`, в проверке частоты нужен 201 и нет 5xx; healthcheck API — `/api/health/ready` |
| 7 | P1 | закрыта | CI: проверка импорта chDB, `REQUIRE_CHDB=1` (пропуск chDB-теста валит прогон), `--cov=src` с порогом 90, смоуки нормализатора, классификатора, пересчёта и идентичности в pytest, `normalization_smoke` и `pulscen_smoke` в CI |
| 8 | P2 | закрыта | тело `multipart/form-data` у загрузки, статусы на маршрут со схемой `ApiErrorDto` и `Retry-After`, `Location` у 201, `date-time`, `uuid`, короткие имена схем и `operationId`; `tests/controller/test_openapi.py`. Примеры из `contracts/` в схему не встраивались |
| 9 | P2 | закрыта | `GET /api/searches/{id}` — `ETag` и `private, no-cache` с 304; списки — `no-store` |
| 10 | P2 | закрыта | `contracts/README.md`; фронтенд пропускает незнакомые коды в `warnings`, `highlights`, `checkReasons`; декодеры проверяют `payload_version`, эталон v1 |
| 11 | P2 | закрыта | `contracts/error-codes.json` сверяется с backend и словарями фронтенда (ru/en), добавлены `storage_unavailable`, `upload_queue_full`, `rate_limited`, `not_found`, `method_not_allowed`, `internal_error`; фильтр `itemType` без `unknown` |
| 12 | P2 | открыта | два представления кандидата, `startPrice` числом и пустые `originNote`/`year`/`source` — несовместимая правка контракта, отложена до следующей версии |
| 13 | P2 | открыта | курсоры списков не делались |
| 14 | P2 | частично | `Retry-After` у 503/504, `HEAD /api/health/live`, при `archiveFailed` ответ 200 без `Location`; `invalid_limit` для `?limit=` и `missing` в ответе `results` не делались |
| 15 | P2 | закрыта | повторяющийся сбой готовности и дообработки — стек один раз, затем `error_type`/`repeated`; `urllib3` и `clickhouse_connect` на уровне ERROR; поля вместо `%s` |
| 16 | P2 | закрыта | тесты на 7 выживших мутантов (вес `catalog`, формула истории, вес истории, ничья по ИНН, `rank`, `wins`, смешанные позиции); `mutmut` в CI не добавлялся |
| 17 | P2 | частично | `hypothesis`: `SearchText`, `RuleQueryInterpreter`, `Score.clamp`, `Accept-Language`, `CsvNoticeReader`, `rfc3339`, ИНН, свойство подтверждённого продавца; свойство кодека архива не делалось |

## Находки

### P1 — исправить до фронтенд-аудитов

#### 1. Серверные нарушения инвариантов отдаются как `422 invalid_request` и теряются в логах

- Где: `backend/src/controller/http/errors.py:81` — `(DomainError, INVALID_REQUEST)` ловит все ошибки моделей. `:123-131`: `handle_known` пишет `INFO "request rejected"` без `exc_info` и возвращает `str(error)` клиенту.
- Сценарий: `domain_error_probe.py`. Сервис бросает `InvalidCandidateError`, `InvalidScoreError(1.7)` или `InvalidProcurementLotError`. Так бывает при дефекте ранжирования, сборки кандидата или при порче строки в ClickHouse при чтении. Ответ — `422 invalid_request` с текстом вроде `"score must be a finite number within 0..1, got 1.7"`. В логе только две строки `INFO`, стека нет. Фронтенд показывает «Запрос некорректен, проверьте данные», повтор не поможет, а дефект не виден при разборе логов по уровню `ERROR`.
- Исправление: отображать на 422 только явный список ошибок ввода. Это `EmptySearchTextError`, `SearchTextTooLongError`, `InvalidCandidateLimitError`, `NoticeFileError` и наследники. Остальные `DomainError` отдавать как 500 через `internal_error` со стеком. Вариант — общий базовый класс `InvalidInputError` в `models/errors.py` для ошибок, вызванных вводом.
- Тест: `tests/controller/test_errors.py::test_server_side_invariant_violation_is_internal` — сервис бросает `InvalidCandidateError`, ответ 500 `internal_error`, в `caplog` есть запись `ERROR` с `exc_info`, текст инварианта не попадает в тело. Поправить `test_service_errors_are_mapped`: сейчас он закрепляет `InvalidQueryItemError` → 422.
- На `60d95d3`: сохраняется, проверено тем же скриптом.

#### 2. Ответ 500 не попадает в журнал запросов, трассировка дублируется не-JSON строками

- Где:
  - `backend/src/controller/http/app.py:49-51` и `middleware.py:48-74`: обработчик `Exception` срабатывает в `ServerErrorMiddleware` снаружи `ServerTimingMiddleware`. Starlette отправляет 500 в обход `send_with_timing` и затем повторно бросает исключение.
  - `docker-compose.yml:180` и `backend/Dockerfile:32`: API запускается командой `uvicorn …` без `--log-config`. Логгер `uvicorn` получает свой текстовый обработчик с `propagate: False`.
- Сценарий:
  - `behavior_probe.py`: у 500 есть `X-Request-Id`, но нет `Server-Timing`. В логе только `ERROR "unhandled error"`, строки `"request completed"` со статусом и длительностью нет.
  - `reraise_probe.py`: исключение выходит из ASGI-приложения после ответа.
  - Запуск `uvicorn src.controller.api.main:build_app --factory --no-access-log` с недоступным ClickHouse, один `GET /api/searches` дал 263 строки лога. Из них 9 в JSON. Остальное — `INFO:     Started server process` и `ERROR:    Exception in ASGI application` с многострочной трассировкой, которая повторяет JSON-запись. README обещает «Логи пишутся в JSON». Сборщик логов по строкам режет такую трассировку на сотни записей, а дашборд по `status` из `"request completed"` не видит 500 вовсе.
- Исправление:
  - Журнал и `Server-Timing` перенести в самый внешний слой: собственный ASGI-middleware, который ловит исключение, сам формирует ответ 500 через `error_response` и не бросает дальше. Либо писать `"request completed"` со `status=500` в `finally`, если ответ не начат.
  - Для uvicorn передать JSON-конфигурацию логирования (`--log-config deploy/logging.json`) или запускать через `src.controller.api.main:run` с `log_config=None`. У логгеров `uvicorn*` включить распространение в корневой.
- Тест:
  - `tests/controller/test_middleware.py::test_unhandled_error_is_logged_once_with_status` — `caplog` содержит одну запись `"request completed"` со `status=500` и `request_id`, исключение не выходит из приложения (`ASGITransport(raise_app_exceptions=True)`), заголовок `Server-Timing` есть.
  - `tests/architecture/test_deployment.py::test_api_command_uses_json_logging` — команда API в Compose и `Dockerfile` задаёт конфигурацию логов.
- На `60d95d3`: сохраняется, команды в Compose и `Dockerfile` (`:36`) не менялись.

#### 3. `requestId` не доходит до сервиса, ML-сервиса и ClickHouse

- Где:
  - `request_id` передаётся только явным `extra` в контроллерах: `search/router.py:32-40`, `upload/router.py:60-63`, `http/errors.py`, `http/middleware.py`.
  - Логи сервиса без него: `service/supplier_search/retrieval/runner.py:21`, `enrichment/loader.py:27`, `service.py:86`, `service/health/service.py:25`.
  - `adapter/client/ml_service/retriever.py:53`: ML получает новый `uuid4()`, заголовка `X-Request-Id` нет.
  - Запросы в ClickHouse идут без `log_comment` и `query_id`.
- Сценарий: `behavior_probe.py` с настоящим `ChannelRunner` и упавшим каналом. Запись `"retrieval channel lexical failed"` пришла с `request_id = None`, а записи контроллера того же запроса — с `probe-req-0001`. По логам нельзя связать отказ канала, обогащения или архива с запросом пользователя, а в `system.query_log` — найти запросы одного поиска. Канал, источник и `search_id` вписаны в текст через `%s`, отдельными полями их нет.
- Исправление, без изменений в сервисном слое:
  - `ContextVar` с идентификатором запроса ставится в `RequestIdMiddleware`.
  - `logging.Filter` в `controller/http/log_format.py` добавляет `request_id` в каждую запись.
  - ML-адаптер читает значение через порт или фабрику из `application` и шлёт заголовок `X-Request-Id`. Поле `requestId` в теле остаётся UUID по `ml_contr.md`.
  - Пул ClickHouse ставит `settings={"log_comment": request_id}`.
  - Канал, источник и `search_id` передавать полями `extra`.
- Тест: `tests/controller/test_log_correlation.py::test_service_logs_carry_request_id` — упавший канал в `ChannelRunner` за HTTP-запросом пишет запись с тем же `request_id`, что и заголовок. `tests/adapter/client/test_ml_service.py::test_request_id_header_is_forwarded`.
- На `60d95d3`: сохраняется.

#### 4. Нет метрик и итогового события поиска

- Где: во всём `backend/src` нет счётчиков и гистограмм, маршрута `/metrics` и зависимостей `prometheus`/`opentelemetry`. В логах поиска есть только `"search requested"` (`search/router.py:32-40`) и `"request completed"` с HTTP-статусом.
- Сценарий: по коду. Пункт 9 чек-листа требует время стадий, отказы каналов, долю `recommended`/`check` и пустые результаты. Сейчас ничего из этого не посчитать. Число кандидатов, статусы, коды предупреждений и каналы есть только в архиве ClickHouse, и только если архив сохранился. Отказы каналов видны лишь как `WARNING` без полей (находка 3).
- Исправление:
  - Итоговое событие `"search completed"` в контроллере из `SearchResult`: `search_id`, `items`, `candidates`, `recommended`, `check`, `warnings` (коды), `channels`, `empty=candidates==0`.
  - Метрики Prometheus без изменения сервиса:
    - `http_requests_total{route,status}` и гистограмма длительности — в middleware;
    - `search_candidates_total{status}`, `search_empty_total`, `search_warnings_total{code}` — в контроллере из результата;
    - `search_stage_seconds{stage}` и `search_channel_failures_total{channel}` — обёртки над портами `CandidateRetriever`, `SearchArchive`, `OfferCatalog` в `application/api.py`;
    - `upload_backlog`, `upload_lots_total{status}` — из `LotRunner.backlog` и сохранённых результатов.
  - `/metrics` закрыть в nginx от внешнего доступа.
  - Трассировка OpenTelemetry ложится на те же обёртки портов и инструментирование FastAPI и httpx в `application` без правок сервиса.
- Тест: `tests/controller/test_metrics.py::test_search_outcome_is_counted` — после поиска с одним `recommended` и одним `check` счётчики выросли на 1 и 1. `::test_failed_channel_is_counted` через обёртку порта.
- На `60d95d3`: сохраняется.

#### 5. Фронтенд раз в секунду получает деталь загрузки целиком

- Где:
  - `backend/src/controller/upload/router.py:69-74` и `mapper.py:87-92`: деталь всегда содержит все закупки и все отклонённые строки. Нет `ETag`/`If-None-Match`, пагинации и фильтра по статусу.
  - `frontend/src/entities/upload/queries.ts:11,33-46`: `POLL_MS = 1000`, пока загрузка обрабатывается.
- Сценарий: `detail_size.py`, 5000 закупок и 200 отклонённых строк. Ответ — **1,64 МБ** (28 КБ после gzip), сериализация — **48 мс** в событийном цикле на каждый опрос, плюс запрос в ClickHouse на все закупки. Обработка 5000 закупок идёт десятки минут. Одна открытая вкладка даёт ≈5,9 ГБ JSON в час, CPU API и нагрузку на пул на всё это время. Каждая следующая вкладка удваивает нагрузку.
- Исправление:
  - Для опроса отдавать сводку: `GET /api/uploads/{id}` с `ETag` по `(processed, counts)`, при совпадении `If-None-Match` — ответ 304 без тела.
  - Закупки отдавать постранично: `GET /api/uploads/{id}/lots?status=&cursor=&limit=` или параметры у детали.
  - Фронтенд опрашивает сводку и перечитывает страницу закупок, только когда изменился `processed`.
- Тест: `tests/controller/test_upload_api.py::test_detail_supports_conditional_get` — повтор с `If-None-Match` даёт 304. `::test_lots_are_paginated` — `limit=20` возвращает 20 закупок и курсор.
- На `60d95d3`: сохраняется.

#### 6. Сквозные проверки не выполняют успешный поиск через настоящий ClickHouse

- Где:
  - `deploy/smoke.sh:37-40`: после миграций проверяются только `/nginx-health`, `/api/health/live` и `index.html`.
  - `docker-compose.yml:214`: healthcheck API — `/api/health/live`. По нему `release.sh` (`up --wait`) принимает релиз.
  - chDB-тесты (`tests/application/test_api_e2e.py`, `test_upload_e2e.py`) идут в процессе через `ChdbGateway`, а не через `clickhouse-connect`. Поэтому `adapter/repository/clickhouse/client.py` и `gateway.py` исключены из покрытия и `mypy`.
  - Playwright-тесты фронтенда (`frontend/e2e/*-fixture.ts`) подменяют API через `page.route`.
- Сценарий: по коду. Релиз, в котором API не может прочитать ClickHouse, проходит CI и активируется. Причины могут быть разные: неверный пароль, несовместимое преобразование типов драйвера, сломанное представление `*_current`. Поиск при этом отвечает 503 или 500, а `/live` — 200.
  - На `60d95d3` в `smoke.sh:46-49` добавлены 30 `POST /api/searches`, но проверяется только наличие хотя бы одного 429. Если все остальные ответы 500 или 503, смоук всё равно проходит.
- Исправление:
  - В `smoke.sh` после миграций: `/api/health/ready` = 200.
  - Засеять одну компанию и предложение через `clickhouse-client`.
  - `POST /api/searches` → 201, переход по `Location` → 200 с тем же `searchId`, `GET /api/suppliers/{id}` → 200.
  - Загрузить CSV из двух закупок → 201, опрашивать до `processed == total`.
  - В проверке частоты требовать хотя бы один 201 и отсутствие 5xx.
  - Healthcheck API для приёмки релиза перевести на `/api/health/ready`.
- Тест: шаги выше в `deploy/smoke.sh` и `tests/architecture/test_deployment.py::test_api_healthcheck_uses_readiness`.
- На `60d95d3`: сохраняется, успех поиска не проверяется.

#### 7. Пропуск chDB-тестов не валит CI, порог покрытия не проверяется

- Где:
  - `pytest.importorskip("chdb")` в 7 модулях: `tests/adapter/repository/test_{read_adapters,search_adapters,search_archive,search_pipeline,upload_store}.py`, `tests/application/test_{api,upload}_e2e.py`.
  - `.github/workflows/ci-cd.yml:71`: `python -m pytest` без `--cov` и без проверки пропусков. `pytest-cov` в CI даже не ставится.
  - `backend/pyproject.toml:97`: `fail_under = 90` нигде не применяется.
- Сценарий:
  - Если колесо `chdb` не встанет (новый Python или платформа) или упадёт импорт, все SQL-адаптеры и сквозные API-тесты молча пропустятся, а CI останется зелёным.
  - На Windows эти модули не идут никогда. Локальное покрытие без них — 83,4 % (`561629f`) и 85,3 % (`60d95d3`), адаптеры ClickHouse покрыты на 28–66 %.
  - В CI нет смоуков `tests/clickhouse/normalization_smoke.py`, `tests/classifier/classifier_smoke.py`, `tests/normalizer/normalizer_smoke.py`, `tests/supplier/{enrich,identity,reidentify,pulscen}_smoke.py`. Локально все, кроме требующего chDB `normalization_smoke`, проходят. Регрессии нормализатора и классификатора, которые питают `offers_normalized` для поиска, CI не увидит.
- Исправление:
  - В `tests/conftest.py` при `REQUIRE_CHDB=1` превращать пропуск модуля с маркером `chdb` в ошибку. В CI задать эту переменную.
  - Шаг `python -m pytest --cov=src --cov-report=term` с проверкой порога; при необходимости порог для Linux отдельно.
  - Добавить недостающие смоуки в CI или перевести их в `test_*.py`.
- Тест: сам шаг CI. Контроль — `pytest -m chdb -q` в CI печатает ненулевое число пройденных тестов, проверка через `--junitxml` или `grep`.
- На `60d95d3`: сохраняется (`ci-cd.yml` добавил только `pip-audit`).

### P2 — бэклог

#### 8. OpenAPI описывает API неточно

- Где:
  - `controller/upload/router.py:52-66`: файл читается вручную, поэтому у `POST /api/uploads` в схеме нет `requestBody`. Поле `file` multipart не описано, Swagger UI и генераторы клиента загрузить файл не могут.
  - `controller/supplier/router.py:13`: 422 не объявлен. FastAPI сам добавляет 422 со схемой `HTTPValidationError` (`{detail: [...]}`), а реальный ответ — `ApiErrorDto`.
  - `search/router.py:23-25`, `upload/router.py:35-37`: один набор статусов на весь роутер. `GET /api/searches` объявляет 404/503/504, `GET /api/uploads` — 400/413/415/429, `POST /api/searches` — 404.
  - Не описаны заголовки ответов: `Location` у 201, `X-Request-Id`, `Server-Timing`, `Retry-After`.
  - `controller/http/schema.py:22`: время сериализуется через `PlainSerializer(return_type=str)`, в схеме `createdAt` — просто `string` без `format: date-time`. Параметры пути `search_id`, `upload_id`, `supplier_id` — `string` без `format: uuid`.
  - Схемы с именами модулей: `src__controller__search__dto__MatchDto`, `…__upload__dto__PurchaseDto`. `operationId` вида `create_search_api_searches_post`.
  - Ни одного примера, хотя они есть в `contracts/`. `ApiErrorDto.code` — свободная строка без перечисления кодов. Ограничения `text ≤ 4000`, `limit 1..50` в схеме запроса не видны.
- Сценарий: `openapi_probe.py` на обеих ревизиях.
- Исправление:
  - Объявить тело загрузки через `openapi_extra` или `File`/`UploadFile` с сохранением ручной проверки размера.
  - Статусы задавать на маршрут.
  - Заголовки ответов — через `responses={201: {"headers": …}}`.
  - Для времени — `WithJsonSchema({"type": "string", "format": "date-time"})`.
  - Пути — `UUID` с переводом ошибки в 404.
  - Явные `title` у DTO и `operation_id`.
  - `openapi_examples` и `json_schema_extra` из `contracts/`.
  - `code: Literal[...]` в `ApiErrorDto` для каждого маршрута.
- Тест: `tests/controller/test_openapi.py` — `app.openapi()` совпадает с закоммиченным `contracts/openapi.json`, у `POST /api/uploads` есть `multipart/form-data` с полем `file`, у всех ответов 4xx/5xx схема `ApiErrorDto`.
- На `60d95d3`: сохраняется, добавлены только 429/503 в общие списки.

#### 9. Неизменяемый результат поиска не кэшируется

- Где: `controller/search/router.py:67-72`. Сохранённый поиск не меняется, но ответ идёт без `ETag` и `Cache-Control`. У изменяемых `GET /api/uploads*` и `GET /api/searches` тоже нет явного `Cache-Control`.
- Сценарий: `behavior_probe.py` — у `GET /api/searches/{id}` нет `etag`, `cache-control`, `last-modified`.
- Исправление: для `GET /api/searches/{id}` — `Cache-Control: private, max-age=86400, immutable` и `ETag: "<searchId>-<payload_version>"` с ответом 304 на `If-None-Match`. Для списков и загрузок — `Cache-Control: no-store` или `no-cache` вместе с `ETag` из находки 5.
- Тест: `tests/controller/test_search_api.py::test_saved_search_is_cacheable` — заголовки на месте, повтор с `If-None-Match` даёт 304.
- На `60d95d3`: сохраняется.

#### 10. Нет правил версионирования контракта, версия архива не проверяется

- Где:
  - `adapter/repository/clickhouse/search_archive/result_dto.py:22,80,123`: `payload_version` пишется, но `decode_result` его не проверяет. Нет тестов на эталонный сохранённый payload: `tests/adapter/repository/test_search_codec.py` проверяет только кодирование туда и обратно.
  - Во фронтенде `shared/api/payload.ts:59-69` (`oneOf`) неизвестное значение перечисления бросает `PayloadFormatError`, и весь ответ не разбирается. Это касается и `warnings`, `highlights`, `checkReasons` (`entities/search/parse.ts:259-265`, `entities/evidence/parse.ts:52-71`).
  - В `contracts/` и README нет правил, какие изменения совместимы. В API нет версии ни в пути, ни в заголовке.
- Сценарий: по коду.
  - После релиза с новым `WarningCode` вкладка со старым бандлом перестаёт открывать любой результат с этим предупреждением.
  - Ужесточение инварианта модели (например, `SearchText`) ломает старые ссылки `GET /api/searches/{id}`. Ответ — 500, или 422 из-за находки 1, вместо понятного «устарело».
- Исправление:
  - `contracts/README.md` с правилами: только добавление полей; новые значения перечислений и переименования — несовместимые изменения; порядок выкладки.
  - Во фронтенде пропускать неизвестные коды в списках `warnings`, `highlights`, `checkReasons` вместо падения.
  - В `decode_result` ветвление по `payload_version` и миграция старых версий.
  - Эталонный payload v1 в `tests/adapter/repository/fixtures/search_payload_v1.json`.
- Тест: `tests/adapter/repository/test_search_codec.py::test_v1_payload_still_decodes`. `frontend/tests/entities/search/parse.test.ts` — неизвестный код предупреждения пропускается, результат разбирается.
- На `60d95d3`: сохраняется.

#### 11. Перечисления и коды ошибок синхронизируются только примерами

- Где:
  - Пары `models/enums.py` ↔ `frontend/src/entities/*/model.ts`, `controller/http/errors.py` ↔ `frontend/src/shared/i18n/locales/*/errors.json`.
  - `frontend/src/entities/search/model.ts:46,49-58`: тип запроса допускает `filters.itemType: "unknown"`, а backend (`search/dto.py:21`) принимает только `goods`/`work`/`service` и отвечает 422.
- Сценарий:
  - `enum_compare.py`: сейчас все 16 перечислений совпадают. Автоматической проверки нет, примеры покрывают не все значения.
  - На `60d95d3` появились коды `storage_unavailable` (503) и `upload_queue_full` (429). Их нет ни в словарях фронтенда, ни в `contracts/*/error.example.json`. Фронтенд показывает общий текст по статусу («Сервер временно недоступен» и «Слишком много запросов») вместо текста по коду.
- Исправление: выгружать OpenAPI в `contracts/openapi.json` (находка 8). Во фронтенде тест сравнивает константы моделей с `enum` из схемы и список кодов ошибок с ключами `errors.json`. `itemType` запроса — отдельный тип без `unknown`.
- Тест: `frontend/tests/entities/contract-enums.test.ts`, `frontend/tests/shared/errors/codes.test.ts`.
- На `60d95d3`: сохраняется, расхождение по двум кодам ошибок появилось.

#### 12. Два разных представления одного кандидата и поля, которые всегда `null`

- Где:
  - `controller/search/dto.py:67-126` и `controller/upload/dto.py:67-110`. У поиска `CandidateDto` с вложенным `history`, `region`, `score`, `rank`, а в `MatchDto` есть `offerId`. У закупок `CompanyDto` с плоскими `similarPurchases`/`wins`/`purchases`, без `region`, `score`, `rank` и `offerId`.
  - Всегда `null`: `ProductDto.originNote` (`upload/dto.py:72`), `PurchaseDto.year` и `source` (`upload/mapper.py:105-108`).
  - Цены и количества поиска и профиля — строки (`plain_decimal`), а `LotSummaryDto.startPrice` — `float` (`upload/dto.py:50`, `mapper.py:76`). README (раздел «HTTP API») обещает «количества и цены — строки».
- Сценарий: по коду. Фронтенд держит два парсера одного понятия: `entities/search/parse.ts` и `entities/recommendation/parse.ts`. Поддерживает ветки `originNote` и `year`, которые backend никогда не заполняет. `startPrice` теряет точность после 2⁵³ копеек.
- Исправление: свести кандидата к одной схеме. Поля `originNote`, `year`, `source` либо заполнять, либо убрать из контракта. `startPrice` отдавать строкой, как остальные денежные значения.
- Тест: контрактный тест, что `CompanyDto` — подмножество `CandidateDto` по общим полям. Пример в `contracts/upload/lot.example.json` с непустыми полями, если их оставят.
- На `60d95d3`: сохраняется.

#### 13. Списки поисков и загрузок без курсора

- Где: `controller/search/router.py:58-64`, `controller/upload/router.py:44-49` — только `limit ≤ 50`. `frontend/src/entities/upload/http.ts:21` запрашивает список без параметров (20 последних) и не листает дальше.
- Сценарий: по коду. После 21-й загрузки самые старые не видны в интерфейсе, хотя открываются по прямой ссылке. Поиски ограничены 50.
- Исправление: курсор `before=<createdAt>_<id>` (порядок `created_at DESC, id` уже стабилен в `search_archive/archive.py:32` и `upload_store/query.py:42`) и поле `next` в ответе. Во фронтенде — «Показать ещё».
- Тест: `tests/controller/test_upload_api.py::test_recent_uploads_page_with_cursor` и аналогичный для поисков. chDB-тест на стабильность порядка при равном `created_at`.
- На `60d95d3`: сохраняется.

#### 14. Мелкие несогласованности кодов и статусов

- Где и что:
  - `limit` вне диапазона в теле поиска даёт `invalid_limit` (`models/search.py:36-37`), а в `?limit=` списков — `invalid_request` (`search/router.py:61`, `upload/router.py:47`).
  - При `archiveFailed` ответ 201 с `Location` на несуществующий ресурс (`search/router.py:54`, `service/supplier_search/service.py:82-89`). Переход по нему даёт 404.
  - `POST /api/uploads/{id}/results` молча отбрасывает неизвестные, незавершённые и упавшие закупки (`service/procurement_upload/service.py:84-97`). Клиент не отличает «нет такой» от «ещё не готова».
  - `503 search_unavailable` и `504 search_timeout` без `Retry-After` (на `60d95d3` он есть только у `storage_unavailable` и `upload_queue_full`).
  - `HEAD /api/health/live` → 405: внешние мониторы с `HEAD` видят отказ.
- Сценарий: `behavior_probe.py` (`limit=0`, `HEAD`), остальное по коду.
- Исправление: единый код `invalid_limit` для всех `limit`. При `archiveFailed` отвечать 200 без `Location`. В ответе `results` поле `missing: [{lotId, reason: notFound|queued|failed}]`. `Retry-After` у 503/504. `HEAD` для health.
- Тест: по одному тесту в `tests/controller/test_errors.py`, `test_search_api.py`, `test_upload_api.py`, `test_health_api.py`.
- На `60d95d3`: сохраняется.

#### 15. Шум в логах при недоступном ClickHouse и текст вместо полей

- Где: `service/health/service.py:25` — `WARNING` с полным стеком на каждую пробу готовности. `service/procurement_upload/runner.py:63` (на `60d95d3` `:71`) — `WARNING` со стеком на каждую попытку дообработки. Шаблоны `"retrieval channel %s failed"`, `"search %s was not archived"`.
- Сценарий: запуск uvicorn с недоступным ClickHouse. Каждые 5 с (`resume_delay_seconds`) пишется трассировка раннера плюс предупреждения `urllib3` и `clickhouse_connect`. Если монитор опрашивает `/api/health/ready`, к ним добавляется стек на каждую пробу.
- Исправление: при повторной одинаковой ошибке писать стек один раз, затем — `WARNING` без стека со счётчиком и полем `error_type`. Канал, источник, `search_id` — полями `extra`. Логгеры `urllib3` и `clickhouse_connect` — уровень `ERROR`.
- Тест: `tests/service/health/test_health.py::test_repeated_failure_logs_stack_once`.
- На `60d95d3`: сохраняется. Логи закупок уже содержат `lot_id`.

#### 16. Тесты ранжирования и мапперов пропускают часть мутаций

- Где и что: `mutate.py`, 23 мутанта, **выжили 7** на обеих проверках (рабочая копия и снимок `561629f`):
  1. `ranking/components.py:10` — вес `CATALOG 0.7 → 0.9`: в `test_ranking.py:22` есть только `stock` и `inferred`.
  2. `components.py:34` — `(similar + wins) / 2 → max(similar, wins)`: точки теста дают одно и то же.
  3. `ranking/ranker.py` — вклад `history` в `total` заменён на `evidence`: `test_ranking.py:44` задаёт вес `history = 0`.
  4. `ranker.py:70` — разбиение ничьей по ИНН заменено на имя: в `test_ranking.py:57-58` имена `twin-a`/`twin-b` упорядочены так же, как ИНН.
  5. `controller/search/mapper.py` — `rank=candidate.rank → rank=1`: в API-тестах один кандидат.
  6. `controller/upload/mapper.py` — `wins=history.similar`: у фейков `similar == wins == 0`.
  7. `service/supplier_search/service.py:93` — `any → all` для `itemsInferred`: нет случая со смешанными позициями.

  Политика, RRF, подсветка, ИНН, `Accept-Language` и отказ каналов ловят все свои мутанты.
- Сценарий: `mutate.py` на копии `backend/` (без chDB-тестов: на Linux часть мутаций 3–6 могла бы поймать `test_search_pipeline`, но это не проверено).
- Исправление и тесты:
  - `test_ranking.py::test_catalog_weight_sits_between_stock_and_inferred`;
  - `::test_history_score_is_mean_of_saturations` при `similar ≠ wins`;
  - `::test_history_weight_moves_total`;
  - `::test_ties_break_by_inn_not_name` с обратным порядком имён;
  - `test_search_api.py::test_ranks_are_passed_through` с тремя кандидатами;
  - `test_upload_api.py::test_company_history_counts` с `similar ≠ wins`;
  - `test_service.py::test_mixed_items_warn_about_inference`.

  Мутационный прогон (`mutmut`, только Linux) по `service/supplier_search/{policy,ranking,fusion,assembly}` — отдельной задачей в CI по расписанию.
- На `60d95d3`: эти файлы и тесты не менялись.

#### 17. Нет свойственных тестов

- Где: `hypothesis` нет в зависимостях и тестах.
- Сценарий: `fuzz.py`. 4000 случайных текстов (смешанные алфавиты, `​`, `﻿`, `½`, арабские цифры, `1e9`, `-3`, до 70 позиций) через `RuleQueryInterpreter` — ни одного падения, не больше 50 позиций. 3000 заголовков `Accept-Language` — ни одного падения. Код устойчив, но это держится на ручных примерах, а не на закреплённых свойствах.
- Исправление: добавить `hypothesis` в `dev` и свойства:
  - `SearchText` идемпотентен и не длиннее 4000;
  - `RuleQueryInterpreter` даёт ≤ 50 позиций с уникальными `id`, непустыми именами и `Quantity.value ≥ 0` либо пустой результат, но не исключение;
  - `Score.clamp` всегда в 0..1;
  - кодек архива: `decode(encode(r)) == r` для произвольного корректного `SearchResult`;
  - `parse_accept_language` тотальна;
  - `CsvNoticeReader` бросает только `NoticeFileError` и наследников;
  - `rfc3339` всегда оканчивается на `Z`.
- Тест: `tests/properties/test_text.py`, `test_codec.py`, `test_notice_csv.py`.
- На `60d95d3`: сохраняется.

## Что уже хорошо

- **Контракт и парсеры согласованы.** Все 16 перечислений ответа совпадают с константами фронтенда. Все примеры `contracts/` проходят DTO туда и обратно (`test_examples_round_trip_through_dto`), набор ключей ответа сверяется с примером (`key_paths`), а фронтенд разбирает каждый пример своими парсерами.
- **Инварианты держат то, что проверяет фронтенд.** `Score` в 0..1 (фронтенд требует `fraction`), ранги 1..n, совпадения ссылаются только на известные позиции (`SearchResult`, `LotResult`), денежные значения неотрицательны (ограничение `CHECK` в ClickHouse, `ProcurementLot`).
- **Ошибки единообразны.** Тело `{code, message, requestId}` у всех 4xx и 5xx, включая 404 маршрута, 405 с `Allow`, битый JSON и ошибки схемы. Для 500 наружу уходит только `internal error`. `requestId` совпадает с заголовком.
- **Строгий ввод.** `extra="forbid"`, `strict=True`: строка в `limit` и лишние поля дают 422. `Location` у обоих 201. Неверный UUID в пути даёт 404, а не 500.
- **JSON-логи без текста запроса.** Поиск логируется только длиной и SHA-256, JSON-форматтер покрыт тестами.
- **Тесты проверяют поведение.** Политика проверяется по правилам и их порядку, граница порога покрытия закреплена, RRF и подсветка ловят все мутанты выборки. Есть архитектурные тесты слоёв и правил кода. Сквозные тесты API и загрузки на chDB проходят полный путь HTTP → сервис → SQL.
- **Сервисный слой готов к трассировке.** Всё внешнее идёт через порты, собранные в `application/api.py`. Метрики и спаны встают обёртками над портами без правок сервиса.
- **Разбор текста устойчив.** Случайные тексты и заголовки не роняют интерпретатор и разбор языка.

## Ограничения проверки

- chDB на Windows недоступен, Docker не запущен. Модули с chDB, `deploy/smoke.sh` и мутационный прогон на Linux не выполнялись. Выжившие мутанты 3–6 мог бы поймать `test_search_pipeline` — это не проверено.
- `mutmut` не запускался (на Windows не работает). Выборка мутантов составлена вручную и не заменяет полный прогон.
- Замеры размера детали загрузки сделаны на синтетических закупках; время запроса в ClickHouse на 5000 строк не измерялось.
- Во время аудита ветка сдвинулась с `561629f` на `60d95d3`. Все находки повторно проверены скриптами на снимке `60d95d3`; номера строк даны по `561629f`, где не оговорено иное.
