CREATE TABLE IF NOT EXISTS supplier_search.supplier_profile_embeddings
(
    index_id String,
    card_id String,
    supplier_inn String,
    category String,
    profile_text String,
    model String,
    model_revision String,
    dimensions UInt16,
    embedding Array(Float32),
    content_hash String,
    imported_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(imported_at)
PARTITION BY index_id
ORDER BY (index_id, card_id);

CREATE TABLE IF NOT EXISTS supplier_search.supplier_profile_indexes
(
    index_id String,
    model String,
    model_revision String,
    dimensions UInt16,
    card_count UInt64,
    supplier_count UInt64,
    vectors_sha256 String,
    cards_sha256 String,
    query_instruction String,
    imported_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(imported_at)
ORDER BY index_id;
