CREATE TABLE IF NOT EXISTS supplier_search.uploads
(
    upload_id UUID,
    file_name String,
    total UInt32,
    rejected UInt32,
    issues String CODEC(ZSTD(3)),
    created_at DateTime64(3, 'UTC'),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1),
    CONSTRAINT valid_total CHECK total > 0
)
ENGINE = ReplacingMergeTree(version)
ORDER BY upload_id;

CREATE VIEW IF NOT EXISTS supplier_search.uploads_current AS
SELECT * FROM supplier_search.uploads FINAL WHERE is_deleted = 0;

CREATE TABLE IF NOT EXISTS supplier_search.upload_lots
(
    upload_id UUID,
    lot_id String,
    position UInt32,
    source_row UInt32,
    title String,
    subject String,
    customer_inn String,
    publish_date String,
    start_price Nullable(Decimal(38, 4)),
    created_at DateTime64(3, 'UTC'),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (upload_id, lot_id);

CREATE VIEW IF NOT EXISTS supplier_search.upload_lots_current AS
SELECT * FROM supplier_search.upload_lots FINAL WHERE is_deleted = 0;

CREATE TABLE IF NOT EXISTS supplier_search.upload_results
(
    upload_id UUID,
    lot_id String,
    status LowCardinality(String),
    products UInt16,
    candidates UInt16,
    payload String CODEC(ZSTD(3)),
    processed_at DateTime64(3, 'UTC'),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1),
    CONSTRAINT valid_status CHECK status IN ('ready', 'needsCheck', 'noCandidates', 'failed')
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (upload_id, lot_id);

CREATE VIEW IF NOT EXISTS supplier_search.upload_results_current AS
SELECT * FROM supplier_search.upload_results FINAL WHERE is_deleted = 0;
