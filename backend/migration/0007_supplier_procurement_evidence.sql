CREATE TABLE IF NOT EXISTS supplier_search.supplier_procurement_evidence
(
    index_id String,
    supplier_inn String,
    category String,
    lot_id String,
    title String,
    publish_date Date,
    customer_inn String,
    source_system String,
    product_names Array(String),
    is_winner UInt8,
    category_lots UInt32,
    category_wins UInt32,
    imported_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(imported_at)
PARTITION BY index_id
ORDER BY (index_id, supplier_inn, category, lot_id);

CREATE TABLE IF NOT EXISTS supplier_search.supplier_evidence_imports
(
    index_id String,
    history_before Date,
    row_count UInt64,
    prepared_sha256 String,
    imported_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(imported_at)
ORDER BY index_id;
