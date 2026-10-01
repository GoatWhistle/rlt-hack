# Backend: сбор поставщиков и хранилище

Сервис собирает компании и их ассортимент из внешних источников и сохраняет их
в ClickHouse. Код полностью асинхронный: источники обходятся конкурентно, а те
же сервисы будет вызывать будущее HTTP API на FastAPI.

## Слои

- `src/models/` — только бизнес-модели: источник, компания, предложение, пакет
  источника и журнал обхода.
- `src/adapter/supplier/` — вся реализация парсинга, по папке на источник:
  каждый адаптер сам знает свои адреса и разметку, сам ходит в сеть и сам
  собирает готовые модели. Общие для всех адаптеров правила — устойчивые UUID и
  хеши в `identity.py`, реквизиты в `inn.py`, чтение sitemap в `sitemap.py`,
  разметка JSON-LD в `jsonld.py`, разбор HTML в `page.py`, ошибки в `errors.py`.
- `src/adapter/repository/clickhouse/` — репозитории и раннер миграций.
- `src/service/supplier/` — бизнес-логика: `SupplierSyncWorker` запускает
  адаптеры всех включённых источников конкурентно и сохраняет их пакеты;
  интерфейсы объявлены в `protocols.py`.
- `src/controller/job/` — команда запуска джобы и её DTO аргументов.
- `src/application/` — конфигурация и сборка зависимостей: там объявлены
  источники и подключены их адаптеры.
- `migration/` — SQL-миграции ClickHouse.

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
```

Переменные окружения: `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_USER`,
`CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DATABASE`, `CLICKHOUSE_SECURE`,
`TASK_DATA_DIR`, `SUPPLIER_DATASET_PATH`, `SUPPLIER_DATASET_REGION`,
`SUPPLIER_FEED_URLS`, `SUPPLIER_SITE_URLS`, флаги адаптеров из таблицы выше,
`SYNC_PARALLEL_SOURCES`, `SYNC_PARALLEL_REQUESTS`, `SYNC_WRITE_BATCH`,
`SYNC_MAX_CARDS`, `SYNC_INTERVAL_SECONDS`, `REQUEST_TIMEOUT`, `LOG_LEVEL`,
`GISP_REGISTRY_PROVIDER`, `GISP_EXPORT_LOCATION`,
`PRODUCTCENTER_WEB_PROVIDER`, `PRODUCTCENTER_MAX_CARDS`, `PRODUCTCENTER_CACHE_DIR`.

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
Успешные страницы кешируются не дольше 24 часов; ошибки HTTP не сохраняются.
Docker Compose держит кеш в томе `productcenter-cache` вне Git. Пакет
публикуется только после полного успешного обхода.

Отдельный живой прогон с отчётом, без записи в ClickHouse:

```sh
uv run --python 3.13 python tests/supplier/productcenter_live.py \
  --cache-dir /tmp/productcenter-cache --out /tmp/productcenter-report.json
```

## Проверки

Без сервера ClickHouse и без сети:

```sh
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' \
  python tests/clickhouse/schema_smoke.py
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
```

Линтер и форматтер:

```sh
uv run --no-project --python 3.13 --with 'ruff>=0.14' ruff check .
uv run --no-project --python 3.13 --with 'ruff>=0.14' ruff format .
```
