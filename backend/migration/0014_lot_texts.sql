CREATE TABLE IF NOT EXISTS supplier_search.lot_texts
(
    lot_id String,
    title String,
    text String,
    terms UInt16,
    participants Array(UUID),
    winners Array(UUID),
    INDEX idx_lot_texts_prefixes arrayDistinct(arrayFlatten(arrayMap(t -> [leftUTF8(t, 3), leftUTF8(t, 4), leftUTF8(t, 5), leftUTF8(t, 6)], arrayFilter(t -> lengthUTF8(t) >= 3, splitByRegexp('[^0-9a-zа-я]+', text))))) TYPE text(tokenizer = array)
)
ENGINE = MergeTree
ORDER BY lot_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS supplier_search.lot_texts_refresh
REFRESH EVERY 1 DAY
TO supplier_search.lot_texts
AS SELECT
    lot_id,
    if(subject != '', subject, procedure) AS title,
    replaceAll(lowerUTF8(concat(subject, ' ', procedure, ' ', arrayStringConcat(products, ' '))), 'ё', 'е') AS text,
    toUInt16(least(65535, length(arrayFilter(t -> t != '', splitByRegexp('[^0-9a-zа-я]+', text))))) AS terms,
    participants,
    winners
FROM
(
    SELECT
        lot_id,
        any(subject) AS subject,
        any(procedure) AS procedure,
        groupUniqArray(100)(product) AS products,
        groupUniqArrayIf(supplier_id, participant) AS participants,
        groupUniqArrayIf(supplier_id, winner) AS winners
    FROM
    (
        SELECT lot_id, subject, procedure_name AS procedure, CAST(NULL, 'Nullable(String)') AS product,
            CAST(NULL, 'Nullable(UUID)') AS supplier_id, false AS participant, false AS winner
        FROM supplier_search.procurement_lots_current
        UNION ALL
        SELECT lot_id, NULL, NULL, product_name, NULL, false, false
        FROM supplier_search.procurement_items_current
        UNION ALL
        SELECT lot_id, NULL, NULL, NULL, supplier_id, true, is_winner = 1
        FROM supplier_search.lot_participations_current
    )
    GROUP BY lot_id
    HAVING notEmpty(participants) AND isNotNull(subject)
)
SETTINGS max_threads = 2, max_insert_threads = 1, max_block_size = 16384, min_insert_block_size_rows = 65536, min_insert_block_size_bytes = 33554432, max_bytes_before_external_group_by = 268435456;

CREATE TABLE IF NOT EXISTS supplier_search.supplier_lots
(
    supplier_id UUID,
    lot_id String,
    won Bool,
    title String,
    text String,
    INDEX idx_supplier_lots_prefixes arrayDistinct(arrayFlatten(arrayMap(t -> [leftUTF8(t, 3), leftUTF8(t, 4), leftUTF8(t, 5), leftUTF8(t, 6)], arrayFilter(t -> lengthUTF8(t) >= 3, splitByRegexp('[^0-9a-zа-я]+', text))))) TYPE text(tokenizer = array)
)
ENGINE = MergeTree
ORDER BY (supplier_id, lot_id)
SETTINGS index_granularity = 1024;

CREATE MATERIALIZED VIEW IF NOT EXISTS supplier_search.supplier_lots_refresh
REFRESH EVERY 1 DAY
DEPENDS ON supplier_search.lot_texts_refresh
TO supplier_search.supplier_lots
AS SELECT supplier_id, lot_id, has(winners, supplier_id) AS won, title, text
FROM supplier_search.lot_texts
ARRAY JOIN participants AS supplier_id
SETTINGS max_threads = 2, max_insert_threads = 1, max_block_size = 8192, min_insert_block_size_rows = 65536, min_insert_block_size_bytes = 33554432;
