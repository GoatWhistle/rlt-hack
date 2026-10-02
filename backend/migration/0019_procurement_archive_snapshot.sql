ALTER TABLE supplier_search.procurement_lots ADD COLUMN IF NOT EXISTS publish_date Nullable(Date);
ALTER TABLE supplier_search.procurement_lots ADD COLUMN IF NOT EXISTS archive_index_id String DEFAULT '';
ALTER TABLE supplier_search.procurement_lots ADD COLUMN IF NOT EXISTS archive_history_before Nullable(Date);
ALTER TABLE supplier_search.lot_participations ADD COLUMN IF NOT EXISTS winner_label_status Enum8('unconfirmed' = 0, 'confirmed' = 1) DEFAULT 'unconfirmed';
CREATE TABLE IF NOT EXISTS supplier_search.procurement_archive_imports
(
    index_id String,
    history_before Date,
    prepared_sha256 String,
    lots UInt64,
    items UInt64,
    participations UInt64,
    status Enum8('importing' = 0, 'completed' = 1),
    recorded_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(recorded_at)
ORDER BY index_id;

CREATE OR REPLACE VIEW supplier_search.procurement_lots_current AS
SELECT * FROM supplier_search.procurement_lots FINAL WHERE is_deleted = 0;
CREATE OR REPLACE VIEW supplier_search.lot_participations_current AS
SELECT * FROM supplier_search.lot_participations FINAL WHERE is_deleted = 0;
