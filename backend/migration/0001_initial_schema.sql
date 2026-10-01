-- Миграция 0001: начальная схема хранения поставщиков, предложений и закупок.
-- Применяется миграционным раннером один раз; повторный запуск идемпотентен,
-- но существующие таблицы не перестраивает. Изменения структуры — новым файлом.
-- version назначает writer: строго возрастает для одного ключа ORDER BY.
-- Изменение = INSERT полной строки. ID стабильны и назначаются приложением.
CREATE DATABASE IF NOT EXISTS supplier_search;

CREATE TABLE IF NOT EXISTS supplier_search.suppliers
(
    supplier_id UUID,
    inn Nullable(String),
    kpps Array(String),
    name String,
    legal_status LowCardinality(String) DEFAULT 'unknown',
    region String,
    website String,
    contacts Map(String, String),
    okved_codes Array(String),
    identity_status Enum8('unverified' = 0, 'verified' = 1, 'conflict' = 2),
    identity_evidence_url String,
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_inn CHECK isNull(inn) OR match(ifNull(inn, ''), '^([0-9]{10}|[0-9]{12})$'),
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY supplier_id;

CREATE TABLE IF NOT EXISTS supplier_search.sources
(
    source_id UUID,
    name String,
    base_url String,
    source_type Enum8('directory' = 1, 'website' = 2, 'feed' = 3, 'price_list' = 4, 'registry' = 5, 'dataset' = 6),
    supplier_id Nullable(UUID), -- NULL для общего каталога многих продавцов.
    ownership_status Enum8('unverified' = 0, 'verified' = 1, 'conflict' = 2),
    ownership_evidence_url String,
    parser_name String,
    enabled UInt8 DEFAULT 1,
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_flags CHECK enabled IN (0, 1) AND is_deleted IN (0, 1)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY source_id;

-- Журнал завершённых попыток, включая ошибки. Повтор доставки использует тот же ID.
CREATE TABLE IF NOT EXISTS supplier_search.crawl_runs
(
    run_id UUID,
    source_id UUID,
    started_at DateTime64(3, 'UTC'),
    finished_at DateTime64(3, 'UTC'),
    status Enum8('success' = 1, 'partial' = 2, 'failed' = 3),
    is_full_catalog UInt8 DEFAULT 0,
    pages_fetched UInt32,
    offers_extracted UInt32,
    parser_version String,
    error_message String,
    version UInt64,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_times CHECK finished_at >= started_at,
    CONSTRAINT valid_full CHECK is_full_catalog IN (0, 1)
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(started_at)
ORDER BY (source_id, started_at, run_id);

-- Снимок одного документа в одном обходе. Полное тело хранится по raw_document_uri.
CREATE TABLE IF NOT EXISTS supplier_search.observations
(
    observation_id UUID,
    run_id UUID,
    source_id UUID,
    observed_at DateTime64(3, 'UTC'),
    url String,
    http_status UInt16,
    content_hash String,
    raw_document_uri String,
    extracted_text String CODEC(ZSTD(3)),
    parser_version String,
    version UInt64,
    CONSTRAINT valid_version CHECK version > 0
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(observed_at)
ORDER BY (source_id, observed_at, observation_id);

CREATE TABLE IF NOT EXISTS supplier_search.offers
(
    offer_id UUID,
    source_id UUID,
    external_id String,
    supplier_id Nullable(UUID),
    seller_status Enum8('unverified' = 0, 'verified' = 1, 'conflict' = 2),
    seller_evidence_url String,
    url String,
    name String,
    description String CODEC(ZSTD(3)),
    item_type Enum8('unknown' = 0, 'goods' = 1, 'work' = 2, 'service' = 3),
    brand String,
    article String,
    attributes Map(String, String),
    source_category String,
    okpd2_code String,
    price Nullable(Decimal(18, 4)),
    currency LowCardinality(String),
    unit String,
    delivery_regions Array(String),
    availability Enum8('unknown' = 0, 'available' = 1, 'unavailable' = 2, 'on_order' = 3),
    supplier_role Enum8('unknown' = 0, 'manufacturer' = 1, 'distributor' = 2, 'reseller' = 3, 'service_provider' = 4),
    role_evidence_url String,
    role_evidence_text String,
    observation_id UUID,
    content_hash String,
    first_seen_at DateTime64(3, 'UTC'),
    last_seen_at DateTime64(3, 'UTC'),
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1),
    CONSTRAINT valid_seller CHECK seller_status != 'verified' OR isNotNull(supplier_id),
    CONSTRAINT valid_price CHECK isNull(price) OR price >= 0,
    CONSTRAINT valid_seen CHECK last_seen_at >= first_seen_at
)
ENGINE = ReplacingMergeTree(version)
ORDER BY offer_id;

CREATE TABLE IF NOT EXISTS supplier_search.catalog_items
(
    catalog_item_id UUID,
    name String,
    description String,
    item_type Enum8('unknown' = 0, 'goods' = 1, 'work' = 2, 'service' = 3),
    parent_id Nullable(UUID),
    okpd2_codes Array(String),
    aliases Array(String),
    attribute_names Array(String),
    status Enum8('provisional' = 0, 'confirmed' = 1, 'merged' = 2),
    merged_into_id Nullable(UUID),
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1),
    CONSTRAINT valid_merge CHECK status != 'merged' OR (isNotNull(merged_into_id) AND merged_into_id != catalog_item_id)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY catalog_item_id;

-- Один текущий результат на предложение. При исправлении меняется значение,
-- а не ключ: старая связь с товаром не должна оставаться активной.
CREATE TABLE IF NOT EXISTS supplier_search.offer_matches
(
    offer_id UUID,
    catalog_item_id Nullable(UUID),
    status Enum8('unmatched' = 0, 'review' = 1, 'accepted' = 2, 'rejected' = 3),
    confidence Float32,
    method LowCardinality(String),
    algorithm_version String,
    offer_content_hash String,
    explanation String,
    matched_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1),
    CONSTRAINT valid_confidence CHECK isFinite(confidence) AND confidence >= 0 AND confidence <= 1,
    CONSTRAINT valid_match CHECK status != 'accepted' OR isNotNull(catalog_item_id)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY offer_id;

-- Модель, ревизия и способ подготовки текста входят в model_key.
-- Векторы разной размерности и разных моделей не сравниваются.
CREATE TABLE IF NOT EXISTS supplier_search.embeddings
(
    entity_type Enum8('catalog_item' = 1, 'offer' = 2, 'procurement_item' = 3),
    entity_id UUID,
    model_key String,
    dimensions UInt16,
    embedding Array(Float32),
    content_hash String,
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1),
    CONSTRAINT valid_vector CHECK dimensions > 0 AND length(embedding) = dimensions
        AND arrayAll(x -> isFinite(x), embedding) AND arrayExists(x -> x != 0, embedding)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (entity_type, model_key, dimensions, entity_id);

-- Поля из исходных CSV. Идентификаторы храним строками без потери ведущих нулей.
CREATE TABLE IF NOT EXISTS supplier_search.procurement_lots
(
    lot_id String,
    procedure_id String,
    reqnum String,
    procedure_name String,
    subject String,
    start_price Nullable(Decimal(18, 2)),
    is_smp Nullable(UInt8),
    customer_inn Nullable(String),
    customer_kpp Nullable(String),
    platform LowCardinality(String),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY lot_id;

CREATE TABLE IF NOT EXISTS supplier_search.procurement_items
(
    procurement_item_id UUID,
    lot_id String,
    source_row_key String,
    product_name String,
    okpd2_code String,
    item_type Enum8('unknown' = 0, 'goods' = 1, 'work' = 2, 'service' = 3),
    requirements Map(String, String),
    quantity Nullable(Decimal(18, 4)),
    unit String,
    catalog_item_id Nullable(UUID),
    match_status Enum8('unmatched' = 0, 'review' = 1, 'accepted' = 2, 'rejected' = 3),
    match_confidence Nullable(Float32),
    match_algorithm_version String,
    match_explanation String,
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1),
    CONSTRAINT valid_match CHECK match_status != 'accepted' OR isNotNull(catalog_item_id)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY procurement_item_id;

CREATE TABLE IF NOT EXISTS supplier_search.lot_participations
(
    lot_id String,
    supplier_inn String,
    supplier_kpp String,
    supplier_id UUID,
    is_winner UInt8,
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_flags CHECK is_winner IN (0, 1) AND is_deleted IN (0, 1)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (lot_id, supplier_inn, supplier_kpp);

-- Читать актуальное состояние через представления: FINAL устраняет версии
-- до фонового слияния; удалённая последняя версия не воскрешает предыдущую.
CREATE VIEW IF NOT EXISTS supplier_search.suppliers_current AS
SELECT * FROM supplier_search.suppliers FINAL WHERE is_deleted = 0;
CREATE VIEW IF NOT EXISTS supplier_search.sources_current AS
SELECT * FROM supplier_search.sources FINAL WHERE is_deleted = 0;
CREATE VIEW IF NOT EXISTS supplier_search.offers_current AS
SELECT * FROM supplier_search.offers FINAL WHERE is_deleted = 0;
CREATE VIEW IF NOT EXISTS supplier_search.catalog_items_current AS
SELECT * FROM supplier_search.catalog_items FINAL WHERE is_deleted = 0;
CREATE VIEW IF NOT EXISTS supplier_search.offer_matches_current AS
SELECT * FROM supplier_search.offer_matches FINAL WHERE is_deleted = 0;
CREATE VIEW IF NOT EXISTS supplier_search.embeddings_current AS
SELECT * FROM supplier_search.embeddings FINAL WHERE is_deleted = 0;
CREATE VIEW IF NOT EXISTS supplier_search.procurement_lots_current AS
SELECT * FROM supplier_search.procurement_lots FINAL WHERE is_deleted = 0;
CREATE VIEW IF NOT EXISTS supplier_search.procurement_items_current AS
SELECT * FROM supplier_search.procurement_items FINAL WHERE is_deleted = 0;
CREATE VIEW IF NOT EXISTS supplier_search.lot_participations_current AS
SELECT * FROM supplier_search.lot_participations FINAL WHERE is_deleted = 0;
