# Backend: HTTP API, сбор поставщиков и хранилище

Сервис собирает компании и их ассортимент из внешних источников, сохраняет их
в ClickHouse и отдаёт поиск поставщиков через HTTP API на FastAPI. Код
полностью асинхронный: источники обходятся конкурентно, запросы API
обслуживаются одним процессом с общим контейнером зависимостей.

Локальная векторизация предложений: [инструкция](../deploy/WORKERS.md).
Проверка на искусственных данных: `python tests/embedding/smoke.py`
в окружении с зависимостями backend и extra `test`.

## Слои

- `src/models/` — только бизнес-модели: источник, компания, предложение, пакет
  источника и журнал обхода.
- `src/adapter/supplier/` — вся реализация парсинга, по папке на источник:
  каждый адаптер сам знает свои адреса и разметку, сам ходит в сеть и сам
  собирает готовые модели. Общие для всех адаптеров правила — устойчивые UUID и
  хеши в `identity.py`, реквизиты в `inn.py`, чтение sitemap в `sitemap.py`,
  разметка JSON-LD в `jsonld.py`, разбор HTML в `page.py`, ошибки в `errors.py`.
- `src/adapter/repository/clickhouse/` — репозитории и раннер миграций.
- `src/adapter/repository/reference/` — справочники из файлов: ОКПД2, рубрики,
  словарь головных слов, разделы каталогов источников и единицы ОКЕИ. Это
  хранилище нормативных данных, поэтому оно и лежит в слое адаптеров: файлы
  читаются здесь, а правила применения живут в сервисах.
- `src/service/normalizer/` — приведение позиций к единой форме: чистка текста,
  разбор названия, характеристики к общему словарю, единицы ОКЕИ, цена за
  базовую единицу, ключ склейки дублей.
- `src/service/classifier/` — код ОКПД2, рубрика и тип позиции по
  детерминированным каналам; таксономия и каналы разнесены по модулям.
- `src/adapter/file/notice_csv/` — разбор CSV извещений о закупках.
- `src/service/supplier_search/` — подбор поставщиков: `SupplierMatcher` (каналы,
  слияние, обогащение, политика, ранжирование) и тонкая обёртка
  `SupplierSearchService` для поиска по тексту.
- `src/service/procurement_upload/` — загрузка файла закупок: деление на
  закупки, фоновая обработка через тот же `SupplierMatcher`, повторы и
  дообработка после перезапуска.
- `src/service/supplier/` — бизнес-логика: `SupplierSyncWorker` запускает
  адаптеры всех включённых источников конкурентно, прогоняет собранный пакет
  через нормализатор и классификатор и сохраняет результат;
  `OfferEnrichmentService` пересчитывает производные значения у уже сохранённых
  позиций. Интерфейсы объявлены в `protocols.py`.
- `src/controller/job/` — команда запуска джобы и её DTO аргументов.
- `src/controller/http/` — FastAPI-приложение: `create_app`, middleware,
  обработчики ошибок, разбор `Accept-Language`; `src/controller/search/`,
  `src/controller/supplier/`, `src/controller/upload/`, `src/controller/health/` —
  роуты, DTO и мапперы;
  `src/controller/api/main.py` — запуск uvicorn.
- `src/application/` — конфигурация и сборка зависимостей: там объявлены
  источники и подключены их адаптеры.
- `migration/` — SQL-миграции ClickHouse.
- `reference/` — файлы справочников: правятся глазами, в коде не дублируются.

## Единый контракт источника

`SupplierProvider` из `src/service/supplier/protocols.py` описывает любой
источник двумя членами: паспортом источника и методом обхода.

```python
class SupplierProvider(Protocol):
    @property
    def source(self) -> Source: ...

    async def fetch(self) -> SupplierPackage: ...
```

`SupplierPackage` — это `Source` плюс списки `Supplier` и `Offer` с уже
назначенными UUID и хешем содержимого. Адаптер ничего не знает о ClickHouse и
журнале, а сервис ничего не знает об адресах, селекторах и форматах.

## Ключ идентичности предложения

`offer_id = uuid5(источник, external_id)`, и на нём висит вся история позиции:
время первой встречи, версии строки, снятие с продажи. Поэтому ключ строится
одним правилом для всех адаптеров — `identity.external_id`:

1. собственный идентификатор источника (`id` фида, `productID`, `sku`,
   артикул) — он надёжнее всего;
2. иначе адрес страницы, если на ней одна позиция;
3. иначе адрес с отпечатком названия — для каталогов, где на одной странице
   перечислены десятки товаров.

Само название в ключ не попадает: отпечаток не меняется от регистра,
пунктуации и лишних пробелов, поэтому косметическая правка в каталоге не
превращает позицию в новую. Правило отпечатка заморожено и намеренно не
использует нормализатор — смена его правил не должна менять идентичность.

Смена правила меняет `offer_id`, поэтому она выполняется отдельной командой
`reidentify`, а не молча при обходе: позиция получает новый ID, сохраняет время
первой встречи, а строка под старым ID помечается удалённой. Повторный запуск
ничего не меняет.

## Нормализация и классификация

Обе подключаются к сервису сбора такими же интерфейсами, как и источники:

```python
class OfferNormalizing(Protocol):
    async def normalize(self, package: SupplierPackage) -> SupplierPackage: ...


class OfferClassifying(Protocol):
    async def classify(self, package: SupplierPackage) -> SupplierPackage: ...
```

`SupplierSyncWorker` вызывает их сразу после обхода и до записи: сначала
нормализацию, затем классификацию — классификатору нужно нормализованное
название. Реализации лежат в `src/service/normalizer/` и
`src/service/classifier/`, сервису сбора они неизвестны, а подмена реализации не
меняет ни воркер, ни хранилище.

Исходные поля не затираются: результат кладётся в модели `Normalization` и
`Classification` рядом с предложением и пишется отдельными колонками
(`normalized_name`, `unit_code`, `unit_name`, `price_per_unit`, `rubric`,
`rubric_name`, `classification_method`, версии правил). На хеш содержимого
предложения производные значения не влияют.

### Что читать: `offers_normalized`

В таблице `offers` лежат и исходные поля источника, и производные — это нужно,
чтобы пересчитать правила и обосновать рекомендацию. Но читать таблицу напрямую
не нужно: для этого есть представление `offers_normalized`, где у каждого смысла
ровно одно поле.

| поле представления | откуда | что было в таблице |
| --- | --- | --- |
| `name` | ядро названия | `name` (исходная строка) и `normalized_name` |
| `rubric`, `rubric_name` | категория для человека | `source_category` — сырой раздел сайта |
| `okpd2_code`, `okpd2_level` | категория для машины | то же |
| `attributes` | канонические ключи | `attributes` и `normalized_attributes` |
| `unit_code`, `unit_name` | единица по ОКЕИ | `unit` — строка источника |
| `price_per_unit`, `price_unit_code` | цена за базовую единицу | только `price` |
| `brand`, `article` | найденные разбором | поля источника, часто пустые |
| `currency` | код ISO | источники пишут и `RUR`, и `RUB` |
| `description` | текст источника как есть | то же |
| `evidence_url` | где подтверждён продавец | раньше ещё и `role_evidence_url` |
| `merge_key` | ключ склейки дублей | `normalized_key` |
| `method`, `confidence`, `evidence` | происхождение кода | — |

Бренд, артикул и код ОКПД2 в самой таблице тоже хранятся в лучшем известном
виде: если разбор нашёл их в названии, а источник не отдал, в колонку попадает
найденное. Откуда взялся код, всегда видно по `classification_method`.

### Конвейер нормализации

Чистка текста (включая лечение чисел, испорченных Excel) → разбор названия на
предмет, бренд, артикул, ГОСТ и размеры → раскрытие сокращений и синонимов →
характеристики к каноническим ключам → единица измерения по ОКЕИ → цена за
базовую единицу → ключ склейки дублей. Разбор — чистые функции без
ввода-вывода, поэтому пакет целиком уходит в пул потоков.

### Каналы классификации

Каналы перебираются по надёжности, первый сработавший выигрывает, а его
основание сохраняется в `classification_evidence`:

| Канал | Что сработало | Уверенность |
| --- | --- | --- |
| `gold` | код пришёл от самого источника | 1.0 |
| `reference` | название совпало с наименованием из справочника ОКПД2 | 0.9 |
| `archive` | такое же название есть в архиве закупок с проставленным кодом | 0.8 |
| `source_map` | раздел каталога источника отображён на код вручную | 0.7 |
| `lexicon` | головное слово из словаря в начале названия | 0.6 |

Если не сработал ни один канал, позиция остаётся без кода с методом `none`:
классификатор не угадывает, а непокрытое видно в отчёте `coverage`. Рубрика не
считается отдельно — это проекция кода ОКПД2 по самому длинному совпавшему
префиксу. Тип позиции выводится из класса кода, а без кода — по обороту в
начале названия («Оказание услуг…», «Выполнение работ…», «Поставка…»).

| Адаптер | Имя | Что берёт | Флаг |
| --- | --- | --- | --- |
| `SupplierDatasetProvider` | `supplier_dataset` | компании из `Поставщики_24-25.csv` | `SUPPLIER_DATASET_PROVIDER` (вкл.) |
| `YmlFeedProvider` | `yml_feed` | YML-фид магазина: товары, цены, параметры | `YML_FEED_PROVIDER` |
| `SchemaOrgWebProvider` | `schema_org_web` | сайт по sitemap и разметке `Product`/`Offer` | `SCHEMA_ORG_WEB_PROVIDER` |
| `OptKatalogWebProvider` | `optkatalog_web` | компании и номенклатуру optkatalog.ru | `OPTKATALOG_WEB_PROVIDER` |
| `AboutPartnerWebProvider` | `aboutpartner_web` | компании и товары aboutpartner.ru | `ABOUTPARTNER_WEB_PROVIDER` |
| `TexZakazWebProvider` | `texzakaz_web` | производителей и их продукцию texzakaz.ru | `TEXZAKAZ_WEB_PROVIDER` |
| `GispRegistryProvider` | `gisp_registry` | записи полного XLSX-экспорта ПП 719 ГИСП | `GISP_REGISTRY_PROVIDER` |
| `ProductCenterWebProvider` | `productcenter_web` | производителей и товары productcenter.ru | `PRODUCTCENTER_WEB_PROVIDER` (выкл.) |
| `MoscowSuppliersProvider` | `moscow_suppliers` | полный нормализованный экспорт поставщиков и оферт zakupki.mos.ru | `MOSCOW_SUPPLIERS_PROVIDER` (выкл.) |
| `PulscenSnapshotProvider` | `pulscen_snapshot` | диагностический снимок страниц pulscen.ru из JSON-файла | `PULSCEN_SNAPSHOT_PATH` (пусто — выключен) |
| `PulscenWebProvider` | `pulscen_web` | компании и товары с ценой pulscen.ru по рубрикам sitemap | `PULSCEN_WEB_PROVIDER` (выкл.), пауза `PULSCEN_DELAY_SECONDS` |

Адреса фидов и сайтов задаются списками `SUPPLIER_FEED_URLS` и
`SUPPLIER_SITE_URLS` — на каждый адрес создаётся свой адаптер. Сколько карточек
берётся с источника за обход, ограничивает `SYNC_MAX_CARDS`.

## Как читаются источники

Публичного API ни один из каталогов не предоставляет: у `texzakaz.ru` и
`aboutpartner.ru` раздел `/api/` закрыт в `robots.txt`, у `optkatalog.ru`
закрыты поиск, сортировка и постраничная навигация. Поэтому машинным
интерфейсом служат sitemap и разметка страниц:

| Источник | Перечень карточек | Разбор карточки |
| --- | --- | --- |
| `texzakaz.ru` | `sitemap.xml`, раздел `/p/` | JSON-LD `Organization`: ИНН в `taxID`, продукция в `knowsAbout` |
| `aboutpartner.ru` | `sitemap-producers.xml`, раздел `/producer/` | JSON-LD `Organization` и `ItemList` с `Product` |
| `optkatalog.ru` | `sitemap.xml`, листья дерева `/postavschiki/` | заголовки блока описания и список `ty-product-feature` |

Предложения каталогов идут без цены: источники публикуют номенклатуру, а не
прайс. Цены приходят из YML-фидов и разметки `Offer` на сайтах поставщиков.

Новый источник — новая папка в `src/adapter/supplier/<name>/` с классом,
реализующим `source` и `fetch`, затем флаг в `src/application/config.py` и ветка
с ним в `Container.providers`. Сервис, хранилище и схема не меняются.

## Сохранение пакета

ProductCenter дополнительно реализует `StreamingSupplierProvider.batches`:
это частичные порции до 32 товаров. Воркер нормализует, классифицирует и
записывает каждую через `save_batch` с общей отметкой начала обхода.
`finish_snapshot` вызывается только после полного успешного окончания
непустого потока. Обрыв оставляет записанные порции и статус partial, не меняя
доступность остальных товаров. Другие адаптеры сохраняют контракт `fetch`.

Пакет — полное состояние источника на момент обхода, поэтому он сохраняется
одной операцией: источник, компании и предложения пишутся полным снимком строки
новой версией, время первой встречи предложения сохраняется, а предложения
источника, которых в пакете нет, снимаются с продажи. Пустой пакет ничего не
снимает: он чаще означает сломанный разбор, чем исчезновение ассортимента.

Исчезнувшие предложения отбираются по отметке обхода: все строки пакета пишутся
с одним `updated_at`, поэтому более старая отметка у предложения источника
означает, что в этом обходе оно не встретилось. Перечислять увиденные
идентификаторы в запросе нельзя — пакет каталога содержит их тысячи, а параметры
запроса уходят в HTTP-форму ClickHouse с ограниченной длиной поля.

## Конкурентность

`SupplierSyncWorker.run_once` запускает все включённые адаптеры одновременно,
число одновременных обходов ограничено `SYNC_PARALLEL_SOURCES`. Сбой одного
источника не отменяет результаты остальных и попадает в его запись журнала.
Внутри адаптера число одновременных запросов к источнику ограничено
`SYNC_PARALLEL_REQUESTS`, а недоступная страница пропускается с предупреждением.
Блокирующие операции — разбор HTML и XML, чтение CSV, запросы к ClickHouse —
выполняются в пуле потоков, поэтому событийный цикл свободен.

Запросы к ClickHouse идут через пул клиентов `GatewayPool`
(`src/adapter/repository/clickhouse/pool/`): клиент драйвера не рассчитан на
одновременные запросы, поэтому каждый запрос берёт свободного клиента из
очереди и возвращает его после ответа или ошибки. Клиенты создаются по мере
надобности, не больше `CLICKHOUSE_POOL_SIZE`, и закрываются все при остановке.
API получает пул такого размера, и каналы поиска с обогащением кандидатов
выполняются параллельно; джоба сбора работает с одним клиентом, как и раньше.

У API три независимых набора клиентов, чтобы фоновая работа не вытесняла
интерактивную:

- интерактивный пул (`CLICKHOUSE_POOL_SIZE`) — поиск, профили, чтение загрузок;
- фоновый пул (`CLICKHOUSE_BACKGROUND_POOL_SIZE`, по умолчанию 2) — обработка
  закупок из загруженных файлов;
- управляющий клиент вне пулов — проба `/api/health/ready` и `KILL QUERY`.

Каждый запрос API уходит со своим `query_id`. Если вызывающий отменён (например,
сработал `SEARCH_TIMEOUT_SECONDS`), пул отправляет `KILL QUERY ... ASYNC` через
управляющий клиент, и слот освобождается сразу после отмены запроса в ClickHouse.
Клиенты API передают в сессии `max_execution_time` = бюджет + 2 с
(`SEARCH_TIMEOUT_SECONDS` для интерактивного пула, `UPLOAD_LOT_TIMEOUT_SECONDS`
для фонового) и `timeout_overflow_mode=throw`, а таймаут ответа HTTP берут из
`CLICKHOUSE_API_QUERY_TIMEOUT`; у джобы ограничения нет, её таймаут — 300 с.

## HTTP API

Все маршруты лежат под `/api`; документация OpenAPI — `/api/docs` и
`/api/openapi.json` (выключается `API_DOCS=false`). Формат запросов и ответов
зафиксирован примерами в [`contracts/`](../contracts): контрактные тесты
сверяют с ними DTO и ответы API.

| Метод | Путь | Ответ |
| --- | --- | --- |
| `POST` | `/api/searches` | 201, результат поиска и `Location: /api/searches/{id}` |
| `GET` | `/api/searches/{searchId}` | 200, сохранённый результат |
| `GET` | `/api/searches?limit=1..50` | 200, последние поиски (по умолчанию 10) |
| `GET` | `/api/suppliers/{supplierId}` | 200, профиль поставщика и его карточки |
| `GET` | `/api/uploads?limit=1..50` | 200, последние загрузки с прогрессом (по умолчанию 20) |
| `POST` | `/api/uploads` | 201, загрузка принята, `Location: /api/uploads/{id}` |
| `GET` | `/api/uploads/{uploadId}` | 200, загрузка, закупки со статусами и отклонённые строки |
| `GET` | `/api/uploads/{uploadId}/lots/{lotId}` | 200, закупка, её рекомендация и прогресс загрузки |
| `POST` | `/api/uploads/{uploadId}/results` | 200, рекомендации выбранных закупок (`{"lotIds": [...]}`) |
| `GET` | `/api/health/live` | 200, `{"status":"ok"}` |
| `GET` | `/api/health/ready` | 200 или 503, `{"ready", "components":[{"name","state"}]}` |

Тело поиска: `text` (обязательно), `limit` (1..50, по умолчанию 20) и
`filters` с `regions` и `itemType` (`goods`, `work`, `service`); лишние поля
отклоняются. Язык ответа выбирается по `Accept-Language` (`ru` или `en`, по
умолчанию `ru`). Время в ответах — RFC 3339 UTC с `Z`, количества и цены —
строки, оценки округлены до 4 знаков. В `contacts.site` попадает только
абсолютный адрес `http(s)`, в `contacts.email` — только адрес вида
`имя@домен`; иначе поле — пустая строка.

Каждый ответ содержит `X-Request-Id` (входящий токен `[A-Za-z0-9-]{8,64}`
сохраняется, иначе выдаётся новый UUID) и `Server-Timing: app;dur=<мс>`.
Ошибки приходят телом `{"code", "message", "requestId"}`:

| HTTP | `code` | Когда |
| --- | --- | --- |
| 422 | `empty_query` | пустой текст |
| 422 | `query_too_long` | текст длиннее 4000 символов |
| 422 | `invalid_limit` | `limit` вне 1..50 |
| 422 | `invalid_request` | тело или параметры не соответствуют схеме |
| 422 | `query_not_understood` | в тексте не нашлось позиций для поиска |
| 404 | `search_not_found` | нет поиска с таким id |
| 404 | `supplier_not_found` | нет поставщика с таким id |
| 400 | `missing_file` | в multipart нет поля `file` |
| 413 | `file_too_large` | файл больше `UPLOAD_MAX_BYTES` |
| 415 | `unsupported_file_type` | не `.csv` или двоичное содержимое (XLSX, XLS, PDF) |
| 422 | `invalid_file` | пустой файл, нет строк данных, неизвестная кодировка |
| 422 | `missing_columns` | нет обязательных колонок `lot_id`, `procedure_name` |
| 422 | `too_many_rows` | строк больше `UPLOAD_MAX_ROWS` |
| 422 | `no_valid_lots` | ни одна строка не прошла проверку |
| 404 | `upload_not_found` | нет загрузки с таким id |
| 404 | `lot_not_found` | в загрузке нет закупки с таким номером |
| 429 | `upload_queue_full` | в очереди больше `UPLOAD_MAX_BACKLOG` закупок; `Retry-After: 60` |
| 429 | `rate_limited` | ограничение частоты nginx; `Retry-After: 1` |
| 404 | `not_found` | неизвестный маршрут |
| 405 | `method_not_allowed` | метод не поддерживается маршрутом |
| 503 | `search_unavailable` | недоступны все каналы поиска |
| 503 | `storage_unavailable` | ClickHouse недоступен; заголовок `Retry-After: 5` |
| 504 | `search_timeout` | превышен `SEARCH_TIMEOUT_SECONDS` |
| 500 | `internal_error` | прочие ошибки, без деталей наружу |

Логи пишутся в JSON; текст поискового запроса в них не попадает — только его
длина и SHA-256.

nginx фронтенда (`deploy/nginx.conf`) ограничивает частоту с одного адреса:
`POST /api/searches` — 2 запроса в секунду с запасом 10, `POST /api/uploads` —
6 в минуту с запасом 3 и не больше двух одновременных. Сверх лимита nginx
отвечает `429 rate_limited` тем же JSON-телом ошибки. Адрес клиента берётся из
`X-Forwarded-For` только от прокси из локальных и частных сетей (Caddy).

```sh
curl -s -X POST http://localhost:8000/api/searches   -H 'Content-Type: application/json' -H 'Accept-Language: ru'   -d '{"text": "Крупа гречневая ядрица 500 кг; рис шлифованный 200 кг", "limit": 20}'
curl -s http://localhost:8000/api/searches/<searchId>
curl -s 'http://localhost:8000/api/searches?limit=5'
curl -s http://localhost:8000/api/suppliers/<supplierId>
curl -s http://localhost:8000/api/health/ready
```

Запуск через Docker Compose из корня репозитория — `docker compose up -d --build api`
(образ `backend/Dockerfile`, цель `api`); через фронтенд API доступен по
`http://localhost:8080/api/`. Локально — `uv run api` из `backend/`.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `API_HOST` | `0.0.0.0` | адрес `uv run api` |
| `API_PORT` | `8000` | порт `uv run api`; в Compose — порт на хосте |
| `API_DOCS` | `true` | документация OpenAPI |
| `SEARCH_TIMEOUT_SECONDS` | `8` | таймаут сценария поиска |
| `SEARCH_RETRIEVAL_DEPTH` | `3` | во сколько раз каналы берут больше кандидатов, чем лимит |
| `SEARCH_COVERAGE_THRESHOLD` | `0.5` | порог покрытия позиций для статуса `recommended` |
| `SEARCH_LEXICAL_POOL` | `500` | сколько карточек отбирает лексический поиск |
| `SEARCH_HISTORY_ENABLED` | `true` | канал поиска по истории закупок |
| `SEARCH_ML_ENABLED` | `false` | ML-канал поиска |
| `ML_SERVICE_URL` | `http://ml:8001` | адрес ML-сервиса |
| `ML_SERVICE_TIMEOUT` | `5` | таймаут запроса к ML-сервису, секунды |
| `CLICKHOUSE_POOL_SIZE` | `4` | сколько одновременных запросов API отправляет в ClickHouse |
| `CLICKHOUSE_MAX_THREADS` | `4` | потоков ClickHouse на один запрос; `0` — значение сервера |
| `CLICKHOUSE_BACKGROUND_POOL_SIZE` | `2` | клиентов ClickHouse для фоновой обработки закупок |
| `CLICKHOUSE_API_QUERY_TIMEOUT` | `15` | таймаут ответа ClickHouse для API, секунды (не меньше бюджета + 4 с) |
| `CLICKHOUSE_API_MAX_MEMORY_USAGE` | `0` | `max_memory_usage` запросов API в байтах; `0` — значение сервера |
| `UPLOAD_MAX_BYTES` | `10485760` | наибольший размер CSV; nginx пропускает до 12 МБ |
| `UPLOAD_MAX_ROWS` | `5000` | наибольшее число строк закупок в файле |
| `UPLOAD_CANDIDATES` | `20` | сколько кандидатов подбирается на закупку |
| `UPLOAD_CONCURRENCY` | `2` | сколько закупок обрабатывается одновременно |
| `UPLOAD_ATTEMPTS` | `3` | попыток на закупку, затем статус `failed` |
| `UPLOAD_LOT_TIMEOUT_SECONDS` | `30` | таймаут обработки одной закупки |
| `UPLOAD_RESUME_INTERVAL_SECONDS` | `60` | как часто незавершённые закупки снова ставятся в очередь |
| `UPLOAD_MAX_BACKLOG` | `10000` | сколько закупок может ждать обработки; не меньше `2 × UPLOAD_MAX_ROWS` по умолчанию |

## Загрузка файла закупок

`POST /api/uploads` принимает multipart с полем `file` — CSV извещений в формате
фронтенда (`frontend/src/entities/notice`): разделитель `;`, `,` или табуляция,
UTF-8 (с BOM или без) либо Windows-1251, обязательные колонки `lot_id` и
`procedure_name`, необязательные `subject`, `start_price`, `customer_inn`,
`publish_date` и прочие. Строки с ошибками (`missingLotId`, `badLotId`,
`duplicateLot`, `missingTitle`, `badPrice`, `badDate`, `columnCount`) не
обрабатываются и возвращаются в `issues`; остальные становятся закупками.

Разбор ограничен по памяти: строка файла длиннее 64 КБ или шапка шире 64 колонок
дают `invalid_file`, записи читаются потоком и чтение прерывается на
`UPLOAD_MAX_ROWS + 1` строке, одновременно разбираются не больше двух файлов, а
сам разбор идёт в пуле потоков. В продакшне память контейнера `api` ограничена
`API_MEMORY_LIMIT` (по умолчанию `768m`).

Каждая закупка обрабатывается в фоне тем же конвейером, что и поиск по тексту:
текст предмета (или названия) → позиции через `RuleQueryInterpreter` →
`SupplierMatcher` → кандидаты с основаниями. Раннер живёт в процессе API
(`asyncio`, `UPLOAD_CONCURRENCY` воркеров) и стартует в lifespan; очередей и
брокеров нет. Транзиентный сбой закупки (недоступность хранилища, отказ
каналов) повторяется до `UPLOAD_ATTEMPTS` раз с растущей паузой и случайным
разбросом, таймаут — не больше одного повтора, ошибки данных не повторяются;
затем закупка получает статус `failed`. Состояние хранится в ClickHouse
(миграция `0006_uploads.sql`: `uploads`, `upload_lots`, `upload_results` на
`ReplacingMergeTree` и представления `*_current`). При старте API и затем каждые
`UPLOAD_RESUME_INTERVAL_SECONDS` закупки без результата, которых нет в работе,
снова ставятся в очередь: перезапуск не теряет работу, а закупка, результат
которой не удалось сохранить, обрабатывается повторно без перезапуска.

Очередь закупок живёт в памяти процесса, поэтому API запускается одним
процессом uvicorn без `--workers` и одной репликой; это проверяет
`tests/architecture/test_deployment.py`.

Статус закупки: `queued` — ждёт обработки, `ready` — лидер рекомендован,
`needsCheck` — лидер требует проверки или есть предполагаемые позиции,
`noCandidates` — кандидатов нет, `failed` — обработать не удалось. Рекомендация
содержит только коды (`checkReasons`, `highlights`, `basis`, `role`), текст для
людей строит фронтенд на языке интерфейса. Примеры ответов — в
[`contracts/upload/`](../contracts/upload).

```sh
curl -s -F 'file=@notices.csv;type=text/csv' http://localhost:8000/api/uploads
curl -s http://localhost:8000/api/uploads/<uploadId>
curl -s http://localhost:8000/api/uploads/<uploadId>/lots/<lotId>
curl -s -X POST http://localhost:8000/api/uploads/<uploadId>/results   -H 'Content-Type: application/json' -d '{"lotIds": ["<lotId>"]}'
```

## Команды

Через Docker Compose из корня репозитория:

```sh
docker compose up -d clickhouse migrate          # хранилище и миграции
docker compose run --rm sync-job providers       # подключённые адаптеры
docker compose run --rm sync-job sync            # обход включённых источников
docker compose run --rm sync-job runs --source <UUID>
```

Локально, с установленными зависимостями из `pyproject.toml`:

```sh
uv run --python 3.13 python main.py migrate
uv run --python 3.13 python main.py providers
uv run --python 3.13 python main.py sync --parallel 4
uv run --python 3.13 python main.py sync --forever
uv run --python 3.13 python main.py sources
uv run --python 3.13 python main.py runs --source <UUID>
uv run --python 3.13 python main.py normalize            # пересчитать сохранённые позиции
uv run --python 3.13 python main.py normalize --limit 100
uv run --python 3.13 python main.py coverage             # отчёт о покрытии
uv run --python 3.13 python main.py reidentify           # перевод на новое правило ключа
```

`normalize` нужен, когда изменились правила или справочники: при обходе
источника позиции нормализуются и классифицируются сами. Команда читает
сохранённые позиции источник за источником и перезаписывает их новой версией
строки.

Переменные окружения: `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_USER`,
`CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DATABASE`, `CLICKHOUSE_SECURE`,
`CLICKHOUSE_MAX_THREADS`, `TASK_DATA_DIR`, `SUPPLIER_DATASET_PATH`, `SUPPLIER_DATASET_REGION`,
`SUPPLIER_FEED_URLS`, `SUPPLIER_SITE_URLS`, флаги адаптеров из таблицы выше,
`SYNC_PARALLEL_SOURCES`, `SYNC_PARALLEL_REQUESTS`, `SYNC_WRITE_BATCH`,
`SYNC_MAX_CARDS`, `SYNC_INTERVAL_SECONDS`, `REQUEST_TIMEOUT`, `REFERENCE_DIR`,
`CLASSIFIER_ARCHIVE_CHANNEL`, `CLASSIFIER_ARCHIVE_LIMIT`, `LOG_LEVEL`,
`GISP_REGISTRY_PROVIDER`, `GISP_EXPORT_LOCATION`,
`PRODUCTCENTER_WEB_PROVIDER`, `PRODUCTCENTER_MAX_CARDS`,
`PRODUCTCENTER_PARALLEL_REQUESTS`, `PRODUCTCENTER_REQUEST_INTERVAL`,
`PRODUCTCENTER_CONNECTION_RETRIES`, `PRODUCTCENTER_CACHE_DIR`.

Московский адаптер включается только после получения проверенного полного
экспорта: `MOSCOW_SUPPLIERS_PROVIDER=true` и `MOSCOW_SUPPLIERS_EXPORT_URL`.
Это адрес JSON-потока, подготовленного из разрешённой выгрузки портала; адрес
официального чтения оферт пока не подтверждён. Каждая страница содержит
`complete: true`, постоянный `snapshot_id`,
`totals: {"suppliers": N, "offers": M}`, массивы
`suppliers`, `offers` и `next` (URL следующей страницы или `null`). У компании
обязательны `id`, `name`, `url`; допустимы `inn`, `region`, `website`. У оферты
обязательны `id`, `supplier_id`, `sku_id`, `name`, `url`, `price`; допустимы
`item_type`, `availability`, `currency`, `unit`. Поставщик должен встретиться
до своей оферты. Повтор страницы/ID, сбой запроса, неверный формат и
расхождение контрольных чисел прерывают обход без сохранения пакета. СТЕ без
оферты в поток не включается.

ГИСП выключен по умолчанию. С пустым `GISP_EXPORT_LOCATION` он обходит открытые
JSON-страницы перечня производителей и реестра продукции через официальные
`/pp719v2/pub/org/b/` и `/pp719v2/pub/prod/b/`. На момент проверки API
сообщал 8 118 организаций и 1 084 900 записей продукции; ответ продукции
ограничен 100 строками на страницу. Провайдер проверяет количество строк
каждой страницы и повторно сверяет общий объём перед публикацией пакета.
Вместо реестра продукции API можно задать полный XLSX-экспорт по HTTPS или
`file:///...`; перечень организаций всё равно читается через API, включая
организации без продукции. Если этот запрос закрыт проверкой доступа, весь
обход завершается ошибкой.
Для локального файла
смонтируйте каталог вне Git в контейнер `sync-job` и задайте путь внутри
контейнера. Пустая настройка или неполный/неизвестный формат завершает обход
ошибкой без записи снимка. Начало официального XLSX и 22 000 реальных строк
проверены, но полная передача XLSX с текущего адреса обрывается. Полный обход
JSON-интерфейса остановился на HTML-проверке доступа вместо JSON. Провайдер
завершает такой ответ ошибкой без записи снимка. До полного обхода провайдер
не включайте.
`PRODUCTCENTER_MAX_CARDS=0` означает полный обход. Положительный лимит
останавливает обход ошибкой без сохранения неполного пакета и годится только
для диагностики. ProductCenter выключен по умолчанию до полного живого прогона.
По умолчанию ProductCenter делает один запрос за раз с интервалом не меньше
секунды между началами запросов. После сетевого отказа он повторяет запрос с
возрастающей паузой до 180 раз (около 90 минут); постоянный отказ завершает
обход ошибкой без фиксации полного снимка. Уже готовые порции товаров сохраняются
по потоковому контракту. Эти ограничения задаются отдельными переменными
`PRODUCTCENTER_PARALLEL_REQUESTS`, `PRODUCTCENTER_REQUEST_INTERVAL` и
`PRODUCTCENTER_CONNECTION_RETRIES`, независимо от других источников.
Успешные страницы кешируются не дольше 48 часов; ошибки HTTP не сохраняются.
Docker Compose держит кеш в томе `productcenter-cache` вне Git. Пакет
фиксируется только после полного успешного обхода; готовые порции товаров
сохраняются раньше, по потоковому контракту.

Отдельный живой прогон с отчётом, без записи в ClickHouse:

```sh
uv run --python 3.13 python tests/supplier/productcenter_live.py \
  --cache-dir /tmp/productcenter-cache --out /tmp/productcenter-report.json
```

## Нагрузочный замер

`bench/` — генератор синтетических данных и замер задержки `POST /api/searches`.
Это инструмент, а не тест; реальные данные он не читает. Генератор наполняет
ClickHouse запросами `INSERT … SELECT` из словарей категорий: 50 000
поставщиков (часть без ИНН и с конфликтом идентичности), 300 источников,
300 000 карточек, сопоставления с каталогом, 100 000 лотов, 300 000 позиций и
участия с победителями. Замер прогоняет 50 разных текстовых запросов
последовательно и конкурентно, считает p50/p95/p99, ошибки и RPS, а разбивку
SQL по стадиям поиска берёт из `system.query_log`.

Скрипт поднимает отдельный проект Compose `rlt-bench` со своим томом, чтобы не
смешивать синтетику с рабочей базой. Из `backend/`:

```sh
uv run python -m bench.run --up --build --seed --out bench.json
uv run python -m bench.run --up --pool-size 1 --max-threads 0
uv run python -m bench.run --sequential 50 --concurrency 8 --requests 100
docker compose -p rlt-bench stop
```

`--seed` наполняет пустую базу и пропускает уже наполненную, `--reset`
очищает таблицы перед наполнением. `--pool-size` и `--max-threads`
пересоздают `api` с другими `CLICKHOUSE_POOL_SIZE` и `CLICKHOUSE_MAX_THREADS`.
Порты по умолчанию — API `8000`, ClickHouse `8123`, поэтому основной проект на
время замера должен быть остановлен или запущен на других портах.

## Проверки

Тесты, линтер, форматтер и типы из `backend/`:

```sh
uv run pytest --cov=src/controller --cov=src.application.config --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Тесты с chDB работают только в Linux. Полный прогон в контейнере — из корня
репозитория `docker compose --profile tests run --rm backend-tests` или
напрямую:

```sh
docker run --rm -v "$PWD/backend:/repo/backend:ro" -v "$PWD/contracts:/repo/contracts:ro"   -v rlt-backend-uv:/root/.cache/uv -w /repo/backend -e UV_PROJECT_ENVIRONMENT=/opt/venv   -e UV_LINK_MODE=copy -e COVERAGE_FILE=/tmp/.coverage -e UV_PYTHON=3.13   ghcr.io/astral-sh/uv:python3.13-bookworm-slim   sh -c "uv sync --all-extras --no-install-project -q && /opt/venv/bin/python -m pytest -p no:cacheprovider"
```

Smoke-проверки джобы без сервера ClickHouse и без сети:

```sh
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' \
  python tests/clickhouse/schema_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' \
  python tests/clickhouse/normalization_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' \
  --with lxml --with cssselect --with httpx --with openpyxl \
  python tests/supplier/job_smoke.py
uv run --no-project --python 3.13 --with lxml --with cssselect --with httpx \
  python tests/supplier/provider_smoke.py
uv run --no-project --python 3.13 --with lxml --with cssselect --with httpx \
  python tests/supplier/productcenter_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' \
  --with lxml --with cssselect --with httpx \
  python tests/supplier/productcenter_job_smoke.py
uv run --no-project --python 3.13 --with httpx \
  python tests/supplier/moscow_suppliers_smoke.py
uv run --no-project --python 3.13 python tests/supplier/worker_smoke.py
uv run --no-project --python 3.13 --with httpx --with openpyxl \
  python tests/supplier/gisp_registry.py
uv run --no-project --python 3.13 --with httpx --with openpyxl \
  python tests/supplier/gisp_api.py
uv run --no-project --python 3.13 python tests/supplier/enrich_smoke.py
uv run --no-project --python 3.13 python tests/supplier/identity_smoke.py
uv run --no-project --python 3.13 python tests/supplier/reidentify_smoke.py
uv run --no-project --python 3.13 python tests/normalizer/normalizer_smoke.py
uv run --no-project --python 3.13 python tests/classifier/classifier_smoke.py
```

Проверки нормализатора и классификатора используют настоящие справочники из
`reference/`: несогласованность словаря и таксономии роняет тест.

Линтер и форматтер:

```sh
uv run --no-project --python 3.13 --with 'ruff>=0.14' ruff check .
uv run --no-project --python 3.13 --with 'ruff>=0.14' ruff format .
```

## Прокси парсеров

Прокси задаётся только в окружении parser-worker через HTTP_PROXY/HTTPS_PROXY;
внутренние сервисы исключаются через NO_PROXY. Поддерживается SOCKS5.
Реквизиты хранятся в серверном env-файле вне Git.
