-- Миграция 0018: опубликованные срезы аналитики каталога.
-- Срез публикуется одной вставкой: читатель видит либо предыдущий срез, либо
-- новый целиком. Идентификатор среза детерминирован областью и моментом
-- расчёта, поэтому повтор после сбоя заменяет ту же строку, а не добавляет новую.
CREATE TABLE IF NOT EXISTS supplier_search.analytics_snapshots
(
    snapshot_id UUID,
    scope_key String,
    definitions_version String,
    as_of DateTime64(3, 'UTC'),
    computed_at DateTime64(3, 'UTC'),
    payload String CODEC(ZSTD(3)),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_deleted CHECK is_deleted IN (0, 1)
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(as_of)
ORDER BY (scope_key, snapshot_id)
TTL toDateTime(as_of) + INTERVAL 35 DAY;

CREATE VIEW IF NOT EXISTS supplier_search.analytics_snapshots_current AS
SELECT * FROM supplier_search.analytics_snapshots FINAL WHERE is_deleted = 0;
