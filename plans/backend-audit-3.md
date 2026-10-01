# Аудит backend 3: архитектура, DDD и ООП

Охват: пункты 3 «Архитектура и слои», 4 «DDD» и 5 «ООП и чистота кода» из [audits.md](audits.md#аудиты-backend). Проверялся весь `backend/src`: сервисы из `main` (`normalizer`, `classifier`, `embedding`, `supplier`), сервисы ветки (`supplier_search`, `procurement_upload`, `supplier_profile`, `health`), их адаптеры и контроллеры, а также `application/{container,api,deferred_gateway,embedding,config}.py`. Ветка `feature/supplier-search-api`, HEAD `561629f`, 2026-10-02. Пулы, лимиты, таймауты, 503 и Docker здесь не повторяются, они разобраны в [backend-audit-1.md](backend-audit-1.md).

## Как проверяли

- Код читали по чек-листу с опорой на `AGENTS.md` (раздел Backend), `backend/README.md`, `ml_contr.md` §2, §7, §8 и `contracts/`.
- `uv run python -m pytest` в `backend/` на Windows: 350 прошли, 7 пропущены (chDB). `tests/architecture` — 14 прошли. `ruff check src` — чисто.
- Временные скрипты лежат вне репозитория, в `%TEMP%/claude/w--Projects-hacks-rlt-hack/1d28b4c7-…/scratchpad/backend-audit3/`:
  - `all_rules.py` — правила `tests/architecture/rules.py` по всему `src`, а не только по `CLEAN_ROOTS`, плюс поиск `Protocol` вне `protocols.py`, исключений вне `errors.py` и `Any`;
  - `shape.py` — глубина вложенности, длина списков параметров, размер классов;
  - `domain_probe.py` — настоящие классы сервиса, модели и `create_app` с фейками из `tests/fakes`;
  - `pyproject.mypy.toml` — копия конфигурации без `exclude` и `ignore_errors`, результат в `mypy_full.txt`.

Код не менялся.

## Резюме

Слои разведены последовательно. `service` и `models` используют только стандартную библиотеку. Контроллеры обращаются к сервисам только через протоколы. Все `Protocol` объявлены в `protocols.py` у потребителя, все исключения лежат в `errors.py`. Политика собрана из подменяемых правил, ранжирование отделено от неё. Объекты-значения поиска сами проверяют свои инварианты. Новый код проходит правила чистоты и `mypy --strict`.

Слабые места — в доменных правилах и на стыках контекстов:

- Каталожное совпадение и роль компании засчитываются по предложению с неподтверждённым продавцом. Кандидат получает `recommended`, хотя §7.7 `ml_contr.md` это запрещает.
- Любой `DomainError`, в том числе нарушение внутреннего инварианта или устаревший архив, уходит клиенту как `422 invalid_request` и пишется в лог на уровне INFO без стектрейса.
- Загрузка повторяет сценарий поиска вручную и теряет его предупреждения и версию конвейера. В контракте загрузки нет `warnings`.
- Контексты связаны через внутренности друг друга (`MatchOutcome`, `RoleResolver`). Часть правил предметной области живёт в SQL адаптеров. Правило валидности ИНН существует в двух версиях.
- `mypy --strict` зелёный только благодаря исключениям. Без них — 40 ошибок в 13 файлах. Архитектурный тест не проверяет код из `main`: там 250 docstring, 106 комментариев и 19 функций длиннее 40 строк.

Находок: **P0 — 0, P1 — 3, P2 — 17**.

## Статус исправлений

Исправления — отдельная задача после аудита. Проверено: `ruff check`, `ruff format --check`, `mypy` (strict), `pytest` на Windows и в Linux-контейнере с chDB и `REQUIRE_CHDB=1` (покрытие 97,95 %), смоуки chDB, `npm run verify` и `npm run e2e`.

| № | Приоритет | Статус | Что сделано |
| --- | --- | --- | --- |
| 1 | P1 | закрыта | `OfferEvidence.backs_supplier`; `stock` и `catalog` только у подтверждённого продавца без конфликта; роль и её основание — `models/company_role.assess_role` по таким предложениям; `noCurrentOffer` проверяет предложения, на которых держатся совпадения. Сценарий и свойственный тест — `tests/service/supplier_search/test_seller_confirmation.py` |
| 2 | P1 | закрыта | `InvalidInputError` для ошибок ввода, на 422 отображаются только они; прочие `DomainError` — 500 `internal_error` со стеком. Декодеры архива и загрузок проверяют `payload_version` и поднимают `CorruptRecordError`; эталон `fixtures/search_payload_v1.json` |
| 3 | P1 | закрыта | `SearchPipeline.run → MatchReport` общий для поиска и загрузки; `LotResult` хранит `pipeline` (payload v2, v1 читается); `warnings` и `pipeline` в рекомендации закупки, контракт и фронтенд (необязательное поле, `WarningNote` у закупки); отказ канала или обогащения переводит закупку в `needsCheck` |
| 4 | P2 | закрыта | `MatchOutcome`/`MatchReport` и роль компании в `models`; профиль не зависит от поиска; правило `service-context` по всему `src`, явное исключение — `classifier → normalizer.text` |
| 5 | P2 | закрыта | адаптер отдаёт `matched_content_hash`, правило — `OfferEvidence.catalog_confirmed` |
| 6 | P2 | открыта | «похожая закупка» по-прежнему в SQL адаптеров; нужна общая выборка текста лота и параметры в `SearchSettings` — отдельная задача вместе с аудитом производительности |
| 7 | P2 | закрыта | `models/inn.py` с контрольной суммой и отсевом заполнителей, адаптеры и `Supplier.has_valid_inn` используют его; фейки на корректных ИНН; `hypothesis`-тесты |
| 8 | P2 | частично | `contacts`, `attributes` — `MappingProxyType`, модели хешируются; объект-значение `Contacts` не вводился |
| 9 | P2 | открыта | разбиение `models/` на подпакеты и отдельная модель чтения предложения — крупный перенос, отложен |
| 10 | P2 | частично | глоссарий в `backend/README.md`; переименования отложены до следующей несовместимой версии контракта |
| 11 | P2 | закрыта | `LotQueue` и `PendingLots` вместо конкретного раннера и широкого хранилища; `BackgroundTask` и `ServiceProvider.background()`, lifespan запускает все фоновые задачи |
| 12 | P2 | открыта | объединение контейнеров и `DeferredGateway` пересекается с пулами из аудита 1 и производительностью (аудит 2), отложено до его отчёта |
| 13 | P2 | закрыта | CLI джоб типизирует зависимости протоколами из `controller/job/protocols.py` |
| 14 | P2 | открыта | стратегии `SnapshotSync`/`StreamingSync` — код сбора из `main`, отдельная задача |
| 15 | P2 | частично | сняты исключения mypy для джобы, контейнера и репозиториев ClickHouse (`_batches`, `__exit__`, LSP `is_measure` через `MeasuredUnit`); остаются `adapter/supplier/*`, `service/supplier/*`, `clickhouse/offer.py` |
| 16 | P2 | частично | правила `protocols-location`, `errors-location`, `service-context` по всему `src`, `no-any` для чистого кода; базовая линия docstring и комментариев кода из `main` не заводилась |
| 17 | P2 | частично | общий `ranking_problem` для `SearchResult` и `LotResult` с проверкой единственности поставщика; статус закупки по-прежнему хранится колонкой (новые правила применяются к новым результатам) |
| 18 | P2 | закрыта | `RetrievalChannel`, `EnrichmentSource` в `models/enums.py`, контрактный тест |
| 19 | P2 | открыта | два стеммера — без изменений |
| 20 | P2 | открыта | семантический поиск ClickHouse как канал — отдельная задача ML |

## Находки

### P1 — исправить до фронтенд-аудитов

#### 1. Совпадение и роль подтверждаются предложением с неподтверждённым продавцом, кандидат получает `recommended`

- Где:
  - `backend/src/service/supplier_search/assembly/match.py:13-14` — `is_catalog` проверяет только `match_status == ACCEPTED`;
  - `match.py:41-43` — `INFERRED` с основанием из любой карточки;
  - `assembly/role.py:45-52` — роль и её основание берутся и у карточек с `seller_status != verified`; `_strength` лишь предпочитает подтверждённые;
  - `policy/current_offer.py:7-10` — достаточно одной подтверждённой карточки среди всех текущих предложений компании, даже не связанной с запрошенными позициями.
- Сценарий (`domain_probe.py`, пункты 5–6):
  - у поставщика с проверенным ИНН есть предложение по позиции с `match_status=accepted` и `seller_status=unverified`;
  - есть и другое, не относящееся к запросу предложение с `seller_status=verified`;
  - совпадение получает `basis=catalog`, роль `distributor` подтверждена основанием неподтверждённого продавца, итог — `status=recommended`, `check_reasons=()`.

  §7.3 и §7.7 `ml_contr.md`: «неподтверждённая связь offer↔supplier исключает recommended».
- Исправление:
  - в `OfferEvidence` добавить свойство `backs_supplier` (`seller_confirmed and not has_conflict`);
  - `is_catalog` требует `backs_supplier`, иначе карточка даёт только `INFERRED` с основанием. Тогда `CoverageRule` (`only_inferred`) сам переведёт кандидата в `check` с `rangeUnconfirmed`;
  - `RoleResolver` берёт основание роли только у карточек с `backs_supplier`, иначе `role_evidence=None` и срабатывает `roleUnconfirmed`;
  - `CurrentOfferRule` проверяет карточки, на которые опираются совпадения, а не любые текущие.
- Тест:
  - в `tests/service/supplier_search/test_policy.py` — сценарий выше даёт `check`;
  - свойственный тест (`hypothesis`) по всем сочетаниям `seller_status × match_status × availability`: если кандидат `recommended`, то каждое совпадение `stock`/`catalog` опирается на предложение с подтверждённым продавцом.

#### 2. Нарушение инварианта модели отдаётся клиенту как `422 invalid_request`

- Где:
  - `backend/src/controller/http/errors.py:81` — `(DomainError, INVALID_REQUEST)`;
  - `errors.py:123-132` — `handle_known` пишет `request rejected` на уровне INFO без `exc_info` и возвращает `str(error)`;
  - `adapter/repository/clickhouse/search_archive/result_dto.py:106,123` и `upload_store/codec.py` — при чтении из хранилища заново вызываются конструкторы моделей.
- Сценарий:
  - `classify(InvalidCandidateError("bug"))` возвращает 422 `invalid_request`. Так же отвечают `InvalidEvidenceError`, `InvalidRankError`, `InvalidSearchResultError` из ошибок сборки и ранжирования. Это ошибки кода, а не запроса;
  - в `domain_probe.py`, пункт 2, сохранён поиск с `limit=60`. Это моделирует ужесточение правила, например `CandidateLimit.MAX` с 60 до 50 или фильтр приватных доменов в `Evidence` из аудита 1. `GET /api/searches/{id}` отвечает `422 {"code":"invalid_limit","message":"candidate limit must be within 1..50"}`, хотя клиент ничего не передавал;
  - `backend/README.md:284` описывает 422 `invalid_request` только как «тело или параметры не соответствуют схеме».
- Исправление:
  - разделить ошибки домена на входные (`InvalidInputError`: `EmptySearchText`, `SearchTextTooLong`, `InvalidCandidateLimit`, ошибки файла извещений) и нарушения инвариантов;
  - на 422 отображать только входные, остальные отдавать как 500 `internal_error` с записью исключения;
  - декодеры архива и загрузок ловят `DomainError` и поднимают ошибку адаптера о повреждённой записи. Для старых `payload_version` нужен путь миграции.
- Тест:
  - `tests/controller/test_errors.py` — `InvalidCandidateError` из сервиса даёт 500, тело `internal error`, лог уровня ERROR со стектрейсом;
  - `tests/adapter/repository/…/search_archive` — архив, нарушающий текущие правила, даёт определённое поведение, а не 422.

#### 3. Загрузка повторяет сценарий поиска и теряет его предупреждения и версию конвейера

- Где:
  - `backend/src/service/procurement_upload/processor.py:28-43` вручную повторяет `SupplierSearchService._run` (`service/supplier_search/service.py:58-73`): разбор, проверка пустого результата, `match`;
  - предупреждения `itemsInferred` (`service.py:92-95`) и `PipelineInfo` в загрузке не формируются;
  - `models/lot_result.py:39-47` — `status` не учитывает предупреждения;
  - `controller/upload/dto.py:105-120` — в `RecommendationDto`/`LotResultDto` нет `warnings` и версии конвейера.
- Сценарий:
  - для закупки упал канал `lexical`, канал `history` вернул кандидатов;
  - в поиске пользователь увидит `channelFailed`, в загрузке закупка получит `ready` или `needsCheck`, и сбой нигде не будет виден, хотя `LotResult.warnings` сохранены в payload;
  - при смене правил по сохранённым результатам загрузок не понять, какой версией конвейера они посчитаны.
- Исправление:
  - выделить в `service/supplier_search` общий сценарий `SearchPipeline.run(query) -> MatchReport(items, candidates, pipeline, warnings)`. Им пользуются и `SupplierSearchService`, и `LotProcessor`;
  - `MatchOutcome`/`MatchReport` перенести в `models` (см. находку 4);
  - в `LotResult` хранить `pipeline`;
  - добавить `warnings` в контракт загрузки (`contracts/upload/lot.example.json`, `results.example.json`) и решить, переводит ли деградация каналов закупку в `needsCheck`.

  Контракт меняется, поэтому это нужно сделать до фронтенд-аудитов.
- Тест:
  - `tests/service/procurement_upload/test_processor.py` — фейковый канал падает, в `LotResult.warnings` есть `channelFailed`, а `pipeline.version` совпадает с поиском;
  - `tests/controller/test_contracts.py` — пример контракта загрузки содержит `warnings`.

### P2 — бэклог

#### 4. Контексты сервиса связаны через внутренние модули друг друга

- Где:
  - `backend/src/service/supplier_profile/service.py:7` — `RoleResolver` берётся из `supplier_search.assembly.role`;
  - `service/procurement_upload/protocols.py:18` — порт `LotMatching` возвращает `MatchOutcome` из реализации `supplier_search/matcher.py`;
  - `service/classifier/service.py:33` и `channels.py:18` используют `normalizer.text`;
  - `tests/architecture/rules.py:66` разрешает `src.service.*` любые импорты внутри `src.service`.
- Обоснование:
  - правило «роль компании по ролям её предложений» (`company_role`, `CONTRIBUTORS`) — доменное и общее для поиска и профиля, но спрятано в модуле сборки кандидата;
  - контракт порта загрузки зависит от модуля с реализацией;
  - перенос `matcher.py` ломает загрузку.
- Исправление:
  - `company_role` и разрешение роли — в `models/company_role.py`, как чистую функцию над `OfferEvidence`;
  - `MatchOutcome` — в `models/match.py`;
  - классификатору передавать `name_stems` внедрением, как уже передаётся `name_key`.
- Тест: новое правило в `tests/architecture/rules.py` — `src.service.<context>` импортирует только свой контекст, `src.service.errors` и `src.models`. Действующие исключения перечисляются явно.

#### 5. Правило «действующего» каталожного совпадения спрятано в SQL адаптера

- Где: `backend/src/adapter/repository/clickhouse/offer_read/mapping.py:57-60` — `MATCH_FIELD` переписывает `accepted` в `review`, если `offer_content_hash` изменился.
- Обоснование:
  - §7.4: `catalog` только при действующем `accepted`;
  - правило определяет основание `catalog` против `inferred` и статус кандидата, но в модели его нет. Тесты сервиса его не видят, проверить его можно только через chDB, который на Windows пропускается.
- Исправление:
  - адаптер отдаёт сырой статус и `matched_content_hash`;
  - `OfferEvidence.catalog_confirmed` считает `match_status == ACCEPTED and matched_content_hash == offer.content_hash`.
- Тест: `tests/models/test_offer_evidence.py` — `accepted` с другим хешем не подтверждает каталог.

#### 6. «Похожая закупка» определяется в адаптерах и по-разному в двух местах

- Где:
  - `backend/src/adapter/repository/clickhouse/participation/history.py:15,86-103` — `MATCH_SHARE = 0.5`, доля общих основ;
  - `history_search/retriever.py:16-17` — `WIN_WEIGHT = 2.0`;
  - текст лота собирается по-разному: в `history_search/query.py:3-15` это `subject` и `product_name`, в `participation/query.py:3-20` — `subject`, `procedure_name` и `product_name`.
- Сценарий:
  - лот, совпавший с позицией только по `procedure_name`, попадает в `PurchaseSummary` («похожие закупки», `pastWins`), но не находится каналом `history`, и наоборот;
  - через `history.item_ids` такой лот создаёт совпадение `INFERRED` (`assembly/assembler.py:77`), а значит влияет на покрытие и статус;
  - бизнес-правило не видно из сервиса и не настраивается.
- Исправление:
  - одно определение текста лота — общий фрагмент в `retrieval/`;
  - порог совпадения и веса — в `SearchSettings`, адаптер получает их параметрами. Или сопоставление позиций с лотами выполняет сервис через порт анализатора.
- Тест: тест на chDB — на одном синтетическом наборе лотов канал истории и сводка участия относят к позиции одни и те же лоты.

#### 7. Два правила валидности ИНН

- Где:
  - `backend/src/service/supplier_search/identity.py:5-9` — только формат `\d{10}|\d{12}`;
  - `adapter/supplier/inn.py:21-35` — контрольная сумма и отсев заполнителей;
  - `models/procurement.py:53` — `customer_inn` не проверяется вовсе.
- Сценарий (`domain_probe.py`, пункт 4):
  - сервис признаёт ИНН `0000000000` действительным, адаптер — нет;
  - в фейках тестов (`tests/fakes/domain.py:57`) ИНН `7801234567` проходит политику, но не проходит контрольную сумму.

  Сейчас адаптеры нормализуют ИНН при сборе, но любой новый путь записи (ML, импорт участников) обходит правило.
- Исправление:
  - объект-значение `Inn` в `models` с контрольной суммой;
  - `Supplier.inn: Inn | None`, адаптеры строят его через `Inn.parse`;
  - `has_valid_inn` удаляется, фейки получают корректные ИНН.
- Тест: `hypothesis` — `Inn.parse` принимает ровно те значения, что `is_valid_inn`. В тесте политики ИНН-заполнитель даёт `innMissing`.

#### 8. Изменяемые словари в «неизменяемых» моделях, контакты без типа

- Где:
  - `backend/src/models/supplier.py:18` (`contacts`), `models/offer.py:32` (`attributes`), `models/normalization.py:21`, `models/embedding.py:13`;
  - `controller/search/mapper.py:74-79` читает контакты по строковым ключам `"email"` и `"phone"`.
- Сценарий (`domain_probe.py`, пункт 3):
  - `hash(Supplier(...))` падает с `TypeError: unhashable type: 'dict'`;
  - `supplier.contacts["email"] = ...` меняет «замороженный» объект.

  `Highlight` и `FusedCandidate` уже оборачивают словари в `MappingProxyType`, эти модели — нет.
- Исправление:
  - `MappingProxyType` в `__post_init__` или кортеж пар;
  - объект-значение `Contacts(site, email, phone)` с проверкой схемы ссылки. Это закрывает и находку 9 аудита 1.
- Тест: `tests/models` — `hash()` работает, запись в `contacts`/`attributes` поднимает `TypeError`.

#### 9. Модель записи `Offer` используется как модель чтения, `models/` — плоская папка из 27 модулей

- Где:
  - `backend/src/adapter/repository/clickhouse/offer_read/mapping.py:72-98` строит `Offer` без `normalization` и `classification`: поиск получает частично заполненный агрегат сбора;
  - в `backend/src/models/` модели сбора, поиска, загрузки и журнала лежат вместе. `AGENTS.md` требует отдельную папку на каждую логическую часть слоя.
- Обоснование: граница контекстов «сбор — поиск — загрузка» в коде не видна. Пустые производные поля в модели чтения выглядят как отсутствие данных.
- Исправление:
  - подпакеты `models/catalog` (Source, Supplier, Offer, Package, Normalization, Classification), `models/search`, `models/upload`, `models/sync`;
  - для поиска — модель чтения карточки предложения только с нужными полями.
- Тест: архитектурное правило — модели `models/search` не импортируют `models/sync`.

#### 10. Язык предметной области расходится между кодом и контрактами

- Где:
  - позиция: `QueryItem`, `items`, `itemId` в поиске против `products`, `productId` и `origin: "notice"` в загрузке (`controller/upload/mapper.py:35-39`). При этом `ProductMatch.item_id`;
  - кандидат: `candidates` в поиске против `companies` в загрузке;
  - «карточка»: в коде так называют `OfferEvidence` (`cards`, `_used_cards` в `assembly/assembler.py:55`), а в `ml_contr.md` §8 карточка — это профиль поставщика;
  - «обогащение» имеет три смысла: пересчёт позиций (`models/enrichment.py`, `service/supplier/enrich.py`), загрузку фактов о кандидатах (`service/supplier_search/enrichment/bundle.py:11`) и обогащение ответа ML (§7);
  - роли: `SupplierRole` — роль продавца в предложении, `CompanyRole` — роль компании;
  - три разных протокола называются `OfferCatalog`: `service/supplier/protocols.py:57`, `supplier_search/protocols.py:30`, `supplier_profile/protocols.py:13`.
- Исправление:
  - глоссарий в `backend/README.md`;
  - переименовать `Enrichment` в `CandidateFacts`, `SupplierRole` в `SellerRole`, локальные `cards` в `offers`, `OfferCatalog` сбора в `StoredOffers`;
  - выровнять имена в контракте загрузки при следующей версии контракта.
- Тест: не нужен, правило закрепляется глоссарием и ревью.

#### 11. Сервис загрузки зависит от конкретного раннера, порты смешивают сценарии и жизненный цикл

- Где:
  - `backend/src/service/procurement_upload/service.py:33` — `runner: LotRunner`, конкретный класс;
  - `controller/upload/protocols.py:9-11` — `start`/`stop` в порту роутера, которому они не нужны;
  - `controller/http/app.py:28-32` — `lifespan` знает только о загрузках;
  - `UploadStore` (`procurement_upload/protocols.py:37-54`) содержит 8 методов, а `LotRunner` использует 2 из них: `pending` и `save_result` (`runner.py:61,100`).
- Обоснование:
  - нарушены ISP и DIP;
  - вторая фоновая задача потребует правки `lifespan` и протокола контроллера;
  - сервис нельзя проверить без настоящего раннера.
- Исправление:
  - протокол `LotQueue.submit` в сервисе;
  - протокол `BackgroundTask` (`start`/`stop`) в `controller/http/protocols.py`, `ServiceProvider.background() -> tuple[BackgroundTask, ...]`;
  - `UploadStore` разделить на хранилище загрузок для сервиса и `PendingLots` для раннера.
- Тест:
  - `tests/service/procurement_upload/test_service.py` — с фейковой очередью;
  - `tests/controller/test_app.py` — `lifespan` запускает и останавливает несколько фоновых задач.

#### 12. Два контейнера, тройная ленивость и разрозненные настройки

- Где:
  - `backend/src/controller/api/main.py:217-218` — API собирает `Container` сбора только ради пула;
  - `application/api.py:47` оборачивает пул в `DeferredGateway`, хотя `Container.api_gateway()` (`container.py:95-98`) не делает ввода-вывода, а `GatewayPool` и так открывает соединение при первом запросе (`pool/gateway.py:58-68`);
  - `DeferredGateway` — адаптер `SqlGateway`, но лежит в `application`;
  - `application/api.py:52-56` переносит в `SearchSettings` 3 поля из 8; значения по умолчанию продублированы в `SearchConfig`/`SearchSettings` и `UploadConfig`/`UploadSettings`;
  - `application/embedding.py:251-261` читает `EMBEDDING_*` из `os.getenv` в обход `AppConfig`.
- Обоснование: сборка ресурса ClickHouse разделена между двумя контейнерами, у одного значения два источника, а конфигурация эмбеддингов не проверяется при старте.
- Исправление:
  - класс `ClickHouseResources` в `application` владеет пулами для API и джоб;
  - `DeferredGateway` убрать;
  - настройки сервиса строить из конфигурации в одном месте, значения по умолчанию держать только в `*Settings`;
  - добавить `EmbeddingConfig` в `AppConfig`.

  Правки затрагивают те же файлы, что и задачи по пулам из аудита 1, их нужно согласовать.
- Тест:
  - `tests/application/test_api.py` — сборка приложения не открывает соединений, `aclose` закрывает всё;
  - тест проверяет, что значения `AppConfig.from_env()` без окружения совпадают с `SearchSettings()` и `UploadSettings()`.

#### 13. Контроллер джоб обращается к адаптерам напрямую, его протоколы не используются

- Где:
  - `backend/src/controller/job/cli.py:103-133` вызывает `container.migrator()`, `sources().list_all()`, `journal().last_runs()`, то есть репозитории ClickHouse без сервисного слоя;
  - `controller/job/protocols.py` объявляет 6 протоколов, но ни один не импортируется: проверено `grep` по `src` и `tests`.
- Обоснование: обход через `application` (пункт 3 чек-листа); протоколы — мёртвый код.
- Исправление: аннотировать методы `Container`, которые использует CLI, типами протоколов из `controller/job/protocols.py`, либо удалить неиспользуемые протоколы.
- Тест: mypy без `ignore_errors` для `src.controller.job.*` (см. находку 15).

#### 14. `SupplierSyncWorker` выбирает поведение через `isinstance` на протоколах

- Где:
  - `backend/src/service/supplier/protocols.py:106-135` — `@runtime_checkable` для `StreamingSupplierProvider`, `StreamingSupplierStorage`, `ResumableSupplierProvider`;
  - `service/supplier/worker.py:75-150` — `sync_provider` длиной 76 строк с двумя ветками;
  - `uuid4()` вызывается прямо в сервисе (`worker.py:127`), в отличие от порта `IdGenerator` поиска;
  - размер батча 32 зашит в код (`worker.py:93`);
  - mypy без исключений: `"SupplierStorage" has no attribute "save_batch"` (`worker.py:93,97,112`).
- Обоснование:
  - частичный снимок — расширение контракта, но статическим типам оно невидимо;
  - `runtime_checkable` проверяет только наличие атрибутов;
  - `AGENTS.md` требует оформлять частичные обновления отдельным изменением контракта.
- Исправление:
  - две явные стратегии: `SnapshotSync` (`fetch` + `save_package`) и `StreamingSync`. Стратегию выбирает контейнер по типу адаптера, хранилище типизировано объединённым протоколом;
  - `IdGenerator` как порт;
  - размер батча — в настройки.
- Тест:
  - `tests/supplier` — обе стратегии с фейками;
  - `mypy --strict` по `src/service/supplier` без `exclude`.

#### 15. `mypy --strict` проходит только благодаря исключениям

- Где: `backend/pyproject.toml:106-115` (`exclude`) и `:123-139` (`ignore_errors` для 12 модулей). Без них — 40 ошибок в 13 файлах (`mypy_full.txt`):
  - `application/container.py:133`: `FileUnitReference.is_measure(unit: FileUnit)` не подходит под `UnitReference.is_measure(unit: Unit)` (`service/normalizer/protocols.py:32`) — нарушение LSP: параметр сужен;
  - `adapter/repository/clickhouse/package.py:48-62`: `_batches` типизирован под `Supplier`, а вызывается с `Offer`;
  - `adapter/repository/clickhouse/offer.py` — 25 ошибок;
  - `adapter/supplier/productcenter_web/provider.py` — 12 ошибок.
- Исправление:
  - обобщённый `_batches[T]`;
  - `Unit` в протоколе сделать параметром типа, или адаптер принимает `Unit`;
  - снимать переопределения по модулю за раз.
- Тест: в CI `mypy --strict` без `exclude` и `ignore_errors`, сначала отдельной задачей с базовым списком.

#### 16. Архитектурный тест не видит код из `main` и ряд правил `AGENTS.md`

- Где: `backend/tests/architecture/rules.py:14-63` — `CLEAN_ROOTS` не включает `service/{normalizer,classifier,embedding,supplier}`, `adapter/supplier`, `adapter/repository/{clickhouse/*.py,reference}`, `application/{container,config,embedding}.py`, `controller/{job,embedding}`, часть `models`. По всему `src` (`all_rules.py`):
  - 250 docstring;
  - 106 комментариев;
  - 19 функций длиннее 40 строк;
  - 4 файла длиннее 250 строк: `clickhouse/offer.py` — 375, `optkatalog_web/provider.py` — 370, `productcenter_web/provider.py` — 389, `application/container.py` — 378. В последнем `providers()` занимает 170 строк.

  Нет правил для:
  - места `Protocol` (вне `protocols.py` — 0, сейчас держится на дисциплине);
  - места исключений (вне `errors.py` — 0);
  - изоляции контекстов сервиса (находка 4);
  - `Any` в новом коде (вне SQL-шлюза — `upload_store/rows.py`, `upload_store/store.py`, `application/deferred_gateway.py`).
- Исправление:
  - добавить правила `protocols-location`, `errors-location`, `service-context`, `no-any` для `CLEAN_ROOTS`;
  - для кода из `main` завести файл базовой линии с текущими нарушениями, который может только уменьшаться;
  - `providers()` превратить в таблицу регистрации источников.
- Тест: на каждое новое правило — тест на нарушение и на чистый код, как в `test_rules.py`; прогон по всему `src` с базовой линией.

#### 17. Инварианты результатов продублированы, статус закупки хранится в двух местах

- Где:
  - `backend/src/models/lot_result.py:28-33` повторяет проверки `models/search_result.py:36-44` (ранги 1..n, совпадения ссылаются на известные позиции);
  - уникальность поставщика в списке кандидатов не проверяется нигде и держится только на ключе словаря в `fusion/rrf.py:32-35`;
  - `Upload.rejected` (`models/upload.py:43-45`) дублирует `NoticeFile.rejected`;
  - статус закупки записывается в колонку (`upload_store/store.py:63-73`) и читается из неё для счётчиков и списка (`upload_store/rows.py:73-84`), но `lot()` и `results()` пересчитывают его из payload (`LotProgress.of`, `store.py:98-115`).
- Сценарий: правило `LotResult.status` меняется, например из-за находки 3. Счётчики загрузки и список показывают старый статус, карточка закупки — новый.
- Исправление:
  - объект-значение `RankedCandidates` с проверками рангов, уникальности поставщика и ссылок на позиции, общий для `SearchResult` и `LotResult`;
  - статус — единственный источник: хранимый, с версией payload, или вычисляемый.
- Тест: `hypothesis` для `RankedCandidates`; тест хранилища — при расхождении хранимого и вычисленного статуса `detail()` и `lot()` отдают одно значение.

#### 18. Каналы, источники обогащения и предупреждения — строки без типа

- Где:
  - `CHANNEL = "lexical"`, `"history"` и `"semantic"` объявлены в адаптерах (`offer_search/retriever.py:15`, `history_search/retriever.py:15`, `client/ml_service/retriever.py:23`);
  - `service/supplier_search/enrichment/loader.py:17-20`;
  - `SearchWarning.subject: str`, `ChannelRank.channel: str`.

  Значения попадают в контракт (`pipeline.channels`, `score.channels`, `warnings.subject`).
- Обоснование: значения контракта задают адаптеры, и новый канал может незаметно изменить контракт.
- Исправление: перечисления `RetrievalChannel` и `EnrichmentSource` в `models/enums.py`, адаптеры ссылаются на них.
- Тест: контрактный тест — значения `channels` и `subject` в примерах входят в перечисления.

#### 19. Две реализации разбора текста

- Где:
  - `backend/src/service/normalizer/text.py:90-105` — собственная обрезка окончаний;
  - `adapter/text/analyzer/analyzer.py:18-56` — Snowball со стоп-словами;
  - SQL `retrieval/terms.py:10-11`;
  - замена «ё» на «е» повторена трижды.
- Обоснование: название позиции при сборе нормализуется одним стеммером, а запрос и тексты лотов — другим. Расхождения основ влияют на поиск и на «похожие закупки», а единого места правила нет.
- Исправление: один порт анализатора текста для нормализатора и поиска, либо явно описать в `backend/README.md`, почему стеммеры разные.
- Тест: на общем словаре позиций основы нормализатора и анализатора совпадают или отличаются по зафиксированному списку.

#### 20. Поиск по эмбеддингам не встроен в ядро как канал

- Где: `backend/src/service/embedding/worker.py:80-85` (`search`) — отдельный семантический поиск по ClickHouse, параллельный клиенту `MlServiceRetriever`. В `EmbeddingWorker` используются `time.monotonic()` и общий `ServiceError` с русскими сообщениями (`worker.py:36,53,60,82,89,96`).
- Обоснование: появляется второй путь «семантики», который не попадает в слияние и политику. Ошибки неразличимы для обработчиков.
- Исправление:
  - адаптер `ClickHouseEmbeddingRetriever` по протоколу `CandidateRetriever`, подключаемый флагом в `ApiContainer.retrievers()`;
  - отдельные ошибки `InvalidEmbeddingBatchError` и `EncoderContractError` в `service/errors.py`.
- Тест: `tests/embedding` — ретривер возвращает `RetrievalHits` с рангами 1..n; ошибки различаются по типу.

## Ответы на вопросы чек-листа

- **Направления зависимостей.**
  - Выдерживаются: `controller → service.errors/models`, `service → models`, `adapter → models`. Это проверено тестом по всему `src`.
  - Обходы:
    - CLI джоб использует репозитории через `Container` (находка 13);
    - API зависит от контейнера джоб ради пула (находка 12);
    - внутри `service` контексты зависят друг от друга (находка 4).
- **Ширина портов.** Порты поиска узкие: `CandidateRetriever` — 2 члена, `SearchArchive` — 3, `DependencyProbe` — 2. Профиль объявляет свой суженный `OfferCatalog`. Широкие порты — `UploadStore` и `OfferCatalog` сбора (CRUD плюс отчёт о покрытии): находки 10 и 11.
- **`ApiContainer` и `Container`.** Оставить один корень сборки для ресурсов ClickHouse и отдельные фабрики сервисов API и джоб (находка 12).
- **`CandidateDraft`, `FusedCandidate`, `Enrichment`.** Оставить в сервисе: это промежуточные структуры конвейера, вне поиска они не используются. В `models` перенести только то, что пересекает границы контекстов: `MatchOutcome` и правило роли компании (находка 4).
- **Ядро для загрузки (фаза 4).**
  - Мешают:
    - `MatchOutcome` лежит в модуле реализации;
    - сценарий продублирован в `LotProcessor`;
    - в `LotResult` нет предупреждений и версии конвейера;
    - сервис зависит от конкретного раннера.
  - Нужны: `SearchPipeline`/`MatchReport` в ядре, `LotQueue` и `BackgroundTask` (находки 3, 4, 11).
- **Инварианты.**
  - Проверяются в моделях: текст, лимит, позиции, ранги, оценки, ссылки оснований, статус кандидата и причины, сводка закупок, лот, загрузка, статус закупки.
  - Держатся на дисциплине сервиса:
    - подтверждённый продавец для `stock`/`catalog`/роли (находка 1);
    - действующий `accepted` (находка 5);
    - валидный ИНН (находка 7);
    - уникальность поставщика (находка 17);
    - неизменяемость словарей (находка 8).
- **§7 `ml_contr.md`.**
  - Выполнены: пункты 1, 2, 6, а также 4 в части `review` (через SQL, находка 5) и 7 в части `conflict`.
  - Не выполнен пункт 7 в части неподтверждённой связи предложения с компанией (находка 1).
  - Пункт 3 выполнен для `stock`, но регион не проверяется — регион фильтруют только каналы.

## Что уже хорошо

- **Слои.** `tests/architecture` проверяет направления импортов по всему `src`. `service` и `models` зависят только от стандартной библиотеки. Контроллеры получают сервисы через протоколы из своих `protocols.py`, `Services.resolve` собирает их один раз при старте.
- **Протоколы и ошибки на месте.** Ни одного `Protocol` вне `protocols.py`, ни одного исключения вне `errors.py` (`all_rules.py`). Порты объявлены у потребителя, поэтому `TextAnalyzer` и `SupplierDirectory` повторяются в нескольких контекстах — это осознанная цена правила.
- **Политика и ранжирование.**
  - `CandidatePolicy` — композиция `PolicyRule`: правило добавляется без правки сервиса.
  - `CandidateRanker`, `ReciprocalRankFusion`, `MatchResolver`, `HighlightComposer` — маленькие классы с одной обязанностью.
  - Порядок кандидатов детерминирован.
- **Богатые объекты-значения.** `SearchText`, `CandidateLimit`, `Score`, `Evidence` (только `http(s)` и время с поясом), `RetrievalHits` (ранги 1..n, поставщик один раз), `SupplierCandidate` (`recommended` ровно тогда, когда нечего проверять), `PurchaseSummary`, `ProcurementLot`, `LotResult.status`.
- **Правила оснований в модели.** `OfferEvidence.evidence` и `role_evidence` вычисляются в модели. `review` не подтверждает каталог. `conflict` у продавца, источника или компании исключает `recommended`.
- **DTO по месту.** HTTP DTO, wire DTO ML и DTO архива отделены от моделей. Хранилище загрузок переиспользует DTO архива, а не дублирует их.
- **Чистота нового кода.** Без комментариев и docstring, функции до 40 строк, файлы до 250, `mypy --strict` без ошибок, `Any` только на границе SQL. Фейки в `tests/fakes` подставляются вместо всех портов.
- **Асинхронность.** Подсчёт BM25, сводки участия, разбор CSV и файловый кэш адаптеров вынесены в `asyncio.to_thread`.

## Ограничения проверки

- ClickHouse и chDB не запускались. Находки 5, 6 и 17 подтверждены чтением SQL и кода, а не прогоном.
- Находка 1 опирается на прочтение §7.7 `ml_contr.md`: неподтверждённая связь предложения, на котором держится совпадение, исключает `recommended`. Если владелец продукта трактует пункт иначе, приоритет можно снизить.
- Метрики качества поиска не измерялись. Находки 6 и 19 описывают риск расхождения, а не измеренную потерю качества.
