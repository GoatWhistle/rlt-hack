CREATE TABLE IF NOT EXISTS supplier_search.moscow_products
(
    run_id UUID,
    product_id UUID,
    source_id UUID,
    external_id String,
    url String,
    name String,
    description String CODEC(ZSTD(3)),
    item_type Enum8('unknown' = 0, 'goods' = 1, 'work' = 2, 'service' = 3),
    category_id String,
    category_path Array(String),
    classifier_codes Map(String, String),
    attributes Map(String, String),
    unit String,
    brand String,
    manufacturer String,
    country String,
    image_urls Array(String),
    raw_json String CODEC(ZSTD(3)),
    content_hash String,
    CONSTRAINT valid_external_id CHECK notEmpty(external_id)
)
ENGINE = MergeTree
ORDER BY (run_id, product_id);

CREATE TABLE IF NOT EXISTS supplier_search.moscow_product_publications
(
    run_id UUID,
    source_id UUID,
    product_count UInt64,
    completed_at DateTime64(3, 'UTC')
)
ENGINE = MergeTree
ORDER BY (source_id, completed_at, run_id);

CREATE VIEW IF NOT EXISTS supplier_search.moscow_products_current AS
SELECT * FROM supplier_search.moscow_products
WHERE run_id = (
    SELECT run_id FROM supplier_search.moscow_product_publications
    ORDER BY completed_at DESC, run_id DESC LIMIT 1
);
