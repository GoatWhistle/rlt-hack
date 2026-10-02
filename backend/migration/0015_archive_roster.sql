-- Множество ИНН поставщиков исходного архива для проверки новизны кандидата.
-- Набор публикуется записью в archive_supplier_sets только после полной вставки строк.
CREATE TABLE IF NOT EXISTS supplier_search.archive_suppliers
(
    set_version String,
    inn String,
    imported_at DateTime64(3, 'UTC') DEFAULT now64(3),
    CONSTRAINT valid_inn CHECK match(inn, '^([0-9]{10}|[0-9]{12})$')
)
ENGINE = ReplacingMergeTree(imported_at)
PARTITION BY set_version
ORDER BY (set_version, inn);

CREATE TABLE IF NOT EXISTS supplier_search.archive_supplier_sets
(
    set_version String,
    row_count UInt64,
    source_name String,
    imported_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(imported_at)
ORDER BY set_version;
