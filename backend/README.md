# Backend: сбор поставщиков и хранилище

Локальная векторизация предложений и поиск: [инструкция](../deploy/WORKERS.md).
Проверка на искусственных данных: `python tests/embedding/smoke.py`
в окружении с зависимостями backend и extra `test`.

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
- `src/adapter/repository/reference/` — справочники из файлов: ОКПД2, рубрики,
  словарь головных слов, разделы каталогов источников и единицы ОКЕИ. Это
  хранилище нормативных данных, поэтому оно и лежит в слое адаптеров: файлы
  читаются здесь, а правила применения живут в сервисах.
- `src/service/normalizer/` — приведение позиций к единой форме: чистка текста,
  разбор названия, характеристики к общему словарю, единицы ОКЕИ, цена за
  базовую единицу, ключ склейки дублей.
- `src/service/classifier/` — код ОКПД2, рубрика и тип позиции по
  детерминированным каналам; таксономия и каналы разнесены по модулям.
- `src/service/registry/` — обогащение компаний по реестру МСП ФНС: роль по
  ОКВЭД и заявленной продукции, загрузка выгрузки реестра. Интерфейсы реестра
  и справочника ролей — в его `protocols.py`.
- `src/adapter/client/msp_registry/` — чтение ZIP-выгрузки реестра МСП;
  `src/adapter/repository/clickhouse/registry.py` — её хранение и поиск по ИНН.
- `src/service/supplier/` — бизнес-логика: `SupplierSyncWorker` запускает
  адаптеры всех включённых источников конкурентно, прогоняет собранный пакет
  через обогащение, нормализатор и классификатор и сохраняет результат;
  `OfferEnrichmentService` пересчитывает производные значения у уже сохранённых
  позиций. Интерфейсы объявлены в `protocols.py`.
- `src/controller/job/` — команда запуска джобы и её DTO аргументов.
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

### Роль компании по реестру МСП

Сразу после обхода и до нормализации воркер вызывает `SupplierEnriching`:

```python
class SupplierEnriching(Protocol):
    async def enrich(self, package: SupplierPackage) -> SupplierPackage: ...
```

Реализация `SupplierRegistryEnricher` ищет компании пакета по ИНН в таблице
`msp_companies` и проставляет `role` и `role_evidence` у компании
(`suppliers_current`). Правило:

1. компания заявила в реестре собственную продукцию (`СвПрод`) — производитель;
2. иначе роль по основному ОКВЭД из `reference/okved_roles.json`, выигрывает
   самый длинный префикс: разделы A–C (01–32) — производитель, 46 —
   дистрибьютор, 45 и 47 — перепродавец, 33, 45.2 и услуги — исполнитель
   услуг;
3. иначе роль остаётся `unknown`.

Основание записывается текстом с кодом, названием ОКВЭД и датой сведений.
Роль и ОКВЭД, которые дал сам источник, реестр не перезаписывает. Компании без
ИНН и вне реестра (крупный бизнес в нём не состоит) проходят без изменений.
Роль предложений (`offers.supplier_role`) обогащение не трогает: она
относится к конкретному товару и задаётся адаптером.

Реестр загружается отдельной командой из заранее скачанной ZIP-выгрузки
открытых данных ФНС (`https://www.nalog.gov.ru/opendata/7707329152-rsmp/`,
около 2 ГБ; сервер ФНС ограничивает скорость, поэтому скачивайте с
продолжением, например `curl -C - -o var/msp/rmsp.zip <адрес выгрузки>`):

```sh
docker compose run --rm sync-job registry-import
uv run --python 3.13 python main.py registry-import --path var/msp/rmsp.zip
```

На сервере реестр загружается вручную workflow «MSP registry import» — см.
[deploy/README.md](../deploy/README.md#реестр-мсп-фнс).

Новая выгрузка заменяет сведения компаний, а выбывшие из реестра удаляются
только после успешной загрузки всех файлов. Пока реестр не загружен,
обогащение ничего не меняет. Пересчёт ролей у уже сохранённых компаний
происходит при следующем обходе их источника.

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
| `GispRegistryProvider` | `gisp_registry` | организации и продукцию реестра ПП 719 ГИСП | `GISP_REGISTRY_PROVIDER` |
| `ProductCenterWebProvider` | `productcenter_web` | производителей и товары productcenter.ru | `PRODUCTCENTER_WEB_PROVIDER` (выкл.) |
| `MoscowSuppliersProvider` | `moscow_suppliers` | полный нормализованный экспорт поставщиков и оферт zakupki.mos.ru | `MOSCOW_SUPPLIERS_PROVIDER` (выкл.) |
| `EisRegistryProvider` | `eis_registry` | поставщиков из реестра контрактов ЕИС zakupki.gov.ru | `EIS_REGISTRY_PROVIDER` (выкл.) |
| `PulscenSnapshotProvider` | `pulscen_snapshot` | диагностический снимок страниц pulscen.ru из JSON-файла | `PULSCEN_SNAPSHOT_PATH` (пусто — выключен) |
| `PulscenWebProvider` | `pulscen_web` | компании и товары с ценой pulscen.ru по рубрикам sitemap | `PULSCEN_WEB_PROVIDER` (выкл.), пауза `PULSCEN_DELAY_SECONDS` |
| `SuplBizWebProvider` | `supl_biz_web` | товары и продавцов supl.biz: sitemap товаров и профилей, состояние страниц | `SUPL_BIZ_WEB_PROVIDER` (выкл.), `SUPL_BIZ_MAX_CARDS` |

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

Supl.biz читается иначе: `sitemap.xml` ведёт на постраничные
`sitemap-proposals.xml?p=N` по 500 товаров и на `sitemap-users.xml` с профилями.
Страница товара содержит JSON `preloadedState` с товаром, ценой и продавцом
вместе с ИНН, страница профиля — реквизиты и контакты; поэтому собираются и
продавцы без товаров, а данные профиля главнее данных со страницы товара.
Sitemap проверяется строго: документ обязан быть `sitemapindex` или `urlset` с
адресами supl.biz, а служебный ответ, пустой файл или недоступная часть
завершают обход ошибкой. Тип позиции остаётся `unknown`: страница не отличает
товар от услуги. Лимит `SUPL_BIZ_MAX_CARDS` диагностический: если страниц больше,
обход завершается ошибкой, а неполный пакет не сохраняется.

Для диагностики Supl.biz есть выборка поровну по 24 корневым категориям:
`PYTHONPATH=. uv run --no-project --python 3.13 --with httpx python
scripts/supl_biz_balanced_sample.py --per-category 60 --concurrency 3 --out <файл вне Git>`.
Внутри категории товары берутся по кругу из подкатегорий (первая страница каждой,
листание закрыто в `robots.txt`), товары с более чем тремя категориями отсекаются
как спам. Результат пишется только в файл, в ClickHouse он не попадает и полным
снимком источника не является.

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

## Порции обработки

Обход, разбор и запись идут порциями у всех источников, но размеры порций
разные, потому что разные и причины их ограничивать.

Потоковый адаптер отдаёт порции сам по `batches(SYNC_BATCH_SIZE)` (32) и
начинает запись ещё во время обхода. Порция здесь мелкая не ради памяти, а ради
потерь: обход идёт медленно, с паузой не меньше секунды между запросами, и
порция задаёт, как часто результат попадает в хранилище и сколько работы
теряет обрыв. Поддерживает такую отдачу пока только `productcenter_web`.

Остальные адаптеры собирают пакет целиком, после чего `package_batches` делит
его порциями `SYNC_WRITE_BATCH` (500) — размером записи, а не обхода. Собранный
пакет уже лежит в памяти целиком, терять в нём нечего, а деление мелкими
порциями умножало бы число INSERT и чтений `first_seen`: пакет на 100 000
предложений дал бы 3 125 INSERT по 32 строки вместо 200 по 500.

Компании идут первыми и отдельно от предложений: обогащение работает только с
компаниями, нормализация и классификация — только с предложениями, поэтому
разделение не меняет результат ни одного шага, а компания записывается один раз
вместо повтора в каждой порции своих предложений.

Деление собранного пакета не делает обход потоковым: адаптер по-прежнему держит
его в памяти целиком.

Внутри порции запись в ClickHouse идёт пачками `SYNC_WRITE_BATCH` — один
INSERT на пачку, поэтому порция размера записи даёт ровно один INSERT.

Снятие отсутствующих предложений с продажи выполняется один раз
после успешного завершения всего обхода: порция этого не делает, иначе
незаконченный обход снял бы с продажи ещё не прочитанные позиции. Пустой пакет
ничего не снимает — это чаще сломанный разбор, чем исчезновение ассортимента.

Эмбеддер работает отдельной джобой и тоже порциями: `EMBEDDING_BATCH_SIZE` (16)
документов за запрос к энкодеру, неполная порция отправляется через
`EMBEDDING_BATCH_WAIT_SECONDS` (5) секунд, векторы пишутся одним INSERT на
порцию. После ошибки незаписанная порция остаётся в выборке и обрабатывается
повторно.

## Что попадает в вектор

`document_text` собирает подписанный текст из названия, ядра названия, типа
позиции, бренда, артикула, характеристик, единицы, раздела каталога, кода ОКПД2,
рубрики, названия компании, её роли и её местоположения — региона вместе с
адресом из контактов. Подписи нужны, чтобы модель отличала регион от бренда.
Цена и наличие в текст не входят: они меняются часто и предмет не уточняют.

Свежесть вектора считается по хешу всего этого набора, а не по `content_hash`
предложения: иначе переезд компании или правка её названия не пересчитали бы
вектор, в который они входят. Хеш считает SQL одним выражением `DOCUMENT_HASH`
на чтении очереди и на поиске, поэтому он не расходится с набором полей,
которые читает тот же запрос. `content_hash` предложения входит в него отдельным
слагаемым: смена правил разбора тоже обязана пересчитать вектор.

## Конкурентность

`SupplierSyncWorker.run_once` запускает все включённые адаптеры одновременно,
число одновременных обходов ограничено `SYNC_PARALLEL_SOURCES`. Сбой одного
источника не отменяет результаты остальных и попадает в его запись журнала.
Внутри адаптера число одновременных запросов к источнику ограничено
`SYNC_PARALLEL_REQUESTS`, а недоступная страница пропускается с предупреждением.
Блокирующие операции — разбор HTML и XML, чтение CSV, запросы к ClickHouse —
выполняются в пуле потоков, поэтому событийный цикл свободен.

## Команды

Каталог продуктов СТЕ хранится отдельно от компаний и оферт. Экспериментальный
обход запускается `MOSCOW_PRODUCTS_PROVIDER=true ... python main.py sync-products`
после миграций `0009_moscow_products.sql` и
`0010_moscow_product_detail_status.sql`. В Docker Compose доступны
`MOSCOW_PRODUCTS_PROVIDER` (по умолчанию `false`) и
`MOSCOW_PRODUCTS_PAGE_SIZE` (по умолчанию 500, проверено живым запросом) и
`MOSCOW_PRODUCTS_RETRY_ATTEMPTS` (по умолчанию 12 попыток для временных сетевых
сбоев и HTTP 429/5xx). Промежуточные строки
помечаются `run_id` и становятся видимы в `moscow_products_current` только
после двух проходов с одинаковым составом ID и сверки числа записей.
Публикуются карточки второго прохода; изменение названий отражает
`names_changed` в результате команды. Недоступные по HTTP 403/404 карточки
остаются позициями списка со статусом `summary_only`; их число выводится как
`summary_only`. Полный живой обход ещё не выполнен, поэтому адаптер выключен.
Для накопления страниц без публикации доступна команда
`MOSCOW_PRODUCTS_PROVIDER=true python main.py collect-products --pages 1`.
Она печатает `run`; следующий запуск с `--run-id <UUID>` продолжает партию
после сверки последнего сохранённого ID с индексом. При сдвиге границы команда
завершается ошибкой до записи следующей страницы. `--pages` ограничивает число
страниц за запуск. Эти строки не видны в `moscow_products_current`, пока
полный каталог не пройдёт отдельную проверку.
`python main.py probe-products` делает один диагностический запрос без ClickHouse
и выводит только счётчик, первый ID, названия полей ответа и структуру первой
доступной карточки.

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
uv run --python 3.13 python main.py registry-import      # загрузка реестра МСП
```

`normalize` нужен, когда изменились правила или справочники: при обходе
источника позиции нормализуются и классифицируются сами. Команда читает
сохранённые позиции источник за источником и перезаписывает их новой версией
строки.

Переменные окружения: `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_USER`,
`CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DATABASE`, `CLICKHOUSE_SECURE`,
`TASK_DATA_DIR`, `SUPPLIER_DATASET_PATH`, `SUPPLIER_DATASET_REGION`,
`SUPPLIER_FEED_URLS`, `SUPPLIER_SITE_URLS`, флаги адаптеров из таблицы выше,
`SYNC_PARALLEL_SOURCES`, `SYNC_PARALLEL_REQUESTS`, `SYNC_WRITE_BATCH`, `SYNC_BATCH_SIZE`,
`SYNC_MAX_CARDS`, `SUPL_BIZ_MAX_CARDS`, `SYNC_INTERVAL_SECONDS`, `REQUEST_TIMEOUT`, `REFERENCE_DIR`,
`CLASSIFIER_ARCHIVE_CHANNEL`, `CLASSIFIER_ARCHIVE_LIMIT`, `LOG_LEVEL`,
`MSP_REGISTRY_PATH` (ZIP-выгрузка реестра МСП; в Compose каталог
`MSP_REGISTRY_DIR`, по умолчанию `./var/msp`, монтируется в `/data/msp`),
`GISP_REGISTRY_PROVIDER`, `GISP_EXPORT_LOCATION`,
`PRODUCTCENTER_WEB_PROVIDER`, `PRODUCTCENTER_MAX_CARDS`,
`PRODUCTCENTER_PARALLEL_REQUESTS`, `PRODUCTCENTER_REQUEST_INTERVAL`,
`PRODUCTCENTER_CONNECTION_RETRIES`, `PRODUCTCENTER_CACHE_DIR`,
`EIS_REGISTRY_PROVIDER`, `EIS_PERIOD_START`, `EIS_PERIOD_DAYS`, `EIS_MAX_CONTRACTS`,
`EIS_CA_BUNDLE`, `EIS_VERIFY_TLS`, `EIS_PROXY`, `EIS_REQUEST_INTERVAL`.

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

ЕИС (`eis_registry`) выключен по умолчанию: разметка подтверждена архивными
снимками 2021–2022 и ручной проверкой живых страниц 1 октября 2026 (только с
российского IP: с зарубежного сайт не отвечает; нужен корневой сертификат НУЦ
Минцифры в `EIS_CA_BUNDLE`), живой прогон адаптера 2 октября 2026 (30 контрактов за день) прошёл успешно, полный сбор не выполнялся.
Адаптер читает HTML-выдачу `/epz/contract/search/results.html` окнами дат
`publishDateFrom/To`. Сайт отдаёт не больше 100 страниц по 50 записей, поэтому
выдача, упёршаяся в лимит, делится пополам по датам, а затем по цене
(`contractPriceFrom/To`); неделимый срез прерывает обход. Для каждого контракта читаются
три страницы карточки: `common-info` (поставщик с ИНН/КПП/адресом, цена, статус,
даты), `payment-info-and-target-of-order` (позиции: ОКПД2/КТРУ, количество,
единица, цена за единицу, сумма) и `process-info` (исполнено и оплачено по
этапам). Пакет содержит только компании; `Offer` не создаются, контракты
остаются в `provider.contracts` до расширения моделей. Сбой сети после повторов,
не тот формат, расхождение числа записей с «Найдено» и лимит `EIS_MAX_CONTRACTS`
завершают обход ошибкой без записи снимка. Снятая карточка (404) пропускается и
считается в отчёте. Переменные: `EIS_REGISTRY_PROVIDER`,
`EIS_PERIOD_START` (ГГГГ-ММ-ДД), `EIS_PERIOD_DAYS` (по умолчанию 30),
`EIS_MAX_CONTRACTS` (0 — без лимита), `EIS_CA_BUNDLE` (путь к сертификату НУЦ
Минцифры), `EIS_VERIFY_TLS`, `EIS_PROXY` (HTTP-прокси с российским выходом), `EIS_REQUEST_INTERVAL` (пауза между запросами, секунды; без неё сайт отвечает 429/403 и блокирует IP). Диагностический живой прогон без записи в БД:
`python tests/supplier/eis_live.py --days 1 --max-contracts 30 --interval 2 \
--proxy http://127.0.0.1:18080 --ca-bundle ru-bundle.pem --out report.json`.

ГИСП выключен по умолчанию. С пустым `GISP_EXPORT_LOCATION` он обходит открытые
JSON-страницы перечня производителей и реестра продукции через официальные
`/pp719v2/pub/org/b/` и `/pp719v2/pub/prod/b/`. На момент проверки API
сообщал 8 118 организаций и 1 084 900 записей продукции; ответ продукции
ограничен 100 строками на страницу. Провайдер проверяет количество строк
каждой страницы и повторно сверяет общий объём перед публикацией пакета.
Прямой HTTP-клиент может получить HTML-проверку доступа. Для воспроизводимого
полного сбора через браузер нужен установленный Google Chrome:

```sh
cd backend
npm ci
npm run gisp:export -- /tmp/gisp-snapshot
SUPPLIER_DATASET_PROVIDER=false GISP_REGISTRY_PROVIDER=true \
  GISP_EXPORT_LOCATION=file:///tmp/gisp-snapshot SYNC_WRITE_BATCH=5000 \
  uv run --python 3.13 python main.py sync --parallel 1
```

Экспорт создаёт `organizations.jsonl`, `products.jsonl` и `manifest.json`
вне Git. После обрыва он продолжает с контрольной точки, сверив число записей
и первую страницу. Провайдер принимает каталог по `file:///...` только при
совпадении числа строк и SHA-256 каждого файла с манифестом; неполный файл не
передаётся в хранилище. Каталог можно смонтировать в контейнер `sync-job` и
задать путь внутри контейнера. Полный живой сбор 1 октября 2026 года дал
8 118 организаций, 1 084 900 записей продукции и пакет из 11 028 компаний и
1 084 900 предложений. Прямая полная передача XLSX с текущего адреса обрывалась;
полный XLSX по HTTPS или `file:///...` по-прежнему поддерживается, но для него
отдельный перечень организаций читается через API.

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

## Проверки

Без сервера ClickHouse и без сети:

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
uv run --no-project --python 3.13 --with lxml --with cssselect --with httpx \
  python tests/supplier/eis_registry_smoke.py
uv run --no-project --python 3.13 --with httpx \
  python tests/product/moscow_smoke.py
uv run --no-project --python 3.13 python tests/product/worker_smoke.py
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
uv run --no-project --python 3.13 --with lxml python tests/registry/registry_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' \
  python tests/registry/registry_store_smoke.py
uv run --no-project --python 3.13 python tests/supplier/batching_smoke.py
uv run --no-project --python 3.13 --with 'chdb==4.1.2' --with 'chdb-core==26.9.0' \
  python tests/embedding/document_smoke.py
uv run --no-project --python 3.13 --with httpx python tests/supplier/supl_biz_smoke.py
PYTHONPATH=. uv run --no-project --python 3.13 --with httpx python tests/supplier/supl_biz_balanced_smoke.py
```

Проверки нормализатора и классификатора используют настоящие справочники из
`reference/`: несогласованность словаря и таксономии роняет тест.

Линтер и форматтер:

```sh
uv run --no-project --python 3.13 --with 'ruff>=0.14' ruff check .
uv run --no-project --python 3.13 --with 'ruff>=0.14' ruff format .
```

## HTTP-поиск и импорт готового индекса

`python -m uvicorn src.controller.search.api:app --host 0.0.0.0 --port 8080`
запускает `/api/health`, `/api/suppliers/search` и `/api/uploads`.
CSV содержит `lot_id,procedure_name,subject`; максимум 20 строк и 2 МБ.
Результаты связаны с cookie сессии и сохраняются в `UPLOADS_DIR`.

`python -m src.controller.search.import_index /data/index` применяет миграции,
проверяет манифест и импортирует карточки/вектора в ClickHouse. Каталог должен
содержать `cards.parquet`, `card_vectors.npy`, `report.json`, `manifest.json`.
`SUPPLIER_INDEX_DIR` задаёт этот каталог для API, `SUPPLIER_INDEX_ID` — SHA-256
массива векторов. При заданном ID косинусная близость считается в ClickHouse;
BM25 и RRF объединяют результаты по ИНН. Незавершённый импорт не публикуется
в реестре готовых индексов. Результаты не заменяются демонстрационными данными.

Прокси задаётся только в окружении parser-worker через HTTP_PROXY/HTTPS_PROXY;
внутренние сервисы исключаются через NO_PROXY. Поддерживается SOCKS5.
Реквизиты хранятся в серверном env-файле вне Git.

### Конфигурация энкодера

Поиск и воркер используют общую фабрику `application/encoder.py`, без подмены
исходников при развёртывании. `EMBEDDING_TRANSPORT=ollama` — значение по умолчанию;
`inference` выбирает совместимый сервис 4B. Настройки передаются файлом
`EMBEDDING_ENV_FILE` (по умолчанию игнорируемый Git `.env.embedding.local`).
Для `inference` обязательны `EMBEDDING_INFERENCE_URL` и
`EMBEDDING_INFERENCE_REVISION`; модель `EMBEDDING_INFERENCE_MODEL` по умолчанию
`Qwen/Qwen3-Embedding-4B`, размерность строго 2560. Токен задаётся только в
серверном окружении как `EMBEDDING_INFERENCE_TOKEN`. Не включайте реквизиты в Git.
`EMBEDDING_INFERENCE_CACHE_KEY` применяется лишь при переносе существующего
совместимого пространства векторов; при смене модели или обработки текста ключ
необходимо обновить. Прокси парсера энкодер не наследует.

Искусственная проверка обоих режимов и некорректных ответов:
`python backend/tests/embedding/inference_smoke.py` из корня проекта.
