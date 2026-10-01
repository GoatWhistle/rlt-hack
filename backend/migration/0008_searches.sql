CREATE TABLE IF NOT EXISTS supplier_search.searches
(
    search_id UUID,
    text String,
    locale LowCardinality(String),
    payload String CODEC(ZSTD(3)),
    candidates UInt16,
    recommended UInt16,
    items UInt16,
    created_at DateTime64(3, 'UTC'),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1),
    CONSTRAINT valid_counts CHECK recommended <= candidates
)
ENGINE = ReplacingMergeTree(version)
ORDER BY search_id;

CREATE VIEW IF NOT EXISTS supplier_search.searches_current AS
SELECT * FROM supplier_search.searches FINAL WHERE is_deleted = 0;
