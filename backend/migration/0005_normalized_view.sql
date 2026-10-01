-- Миграция 0005: каноническое представление нормализованных позиций.
-- В таблице offers остаются и исходные поля источника, и производные: по ним
-- пересчитываются правила и обосновывается рекомендация. Но читать таблицу
-- напрямую не нужно — для этого есть offers_normalized, где у каждого смысла
-- ровно одно поле: одно название, одна категория, одни характеристики, одна
-- единица измерения.
-- Названия рубрики и единицы хранятся рядом с кодами: это такие же
-- производные значения, они считаются вместе с остальными и помечены той же
-- версией правил, поэтому расходиться со справочником не могут.
ALTER TABLE supplier_search.offers
    ADD COLUMN IF NOT EXISTS unit_name String,
    ADD COLUMN IF NOT EXISTS rubric_name String;

-- Представление с SELECT * фиксирует список колонок при создании, поэтому
-- после добавления колонок его приходится пересоздавать.
CREATE OR REPLACE VIEW supplier_search.offers_current AS
SELECT * FROM supplier_search.offers FINAL WHERE is_deleted = 0;

CREATE OR REPLACE VIEW supplier_search.offers_normalized AS
SELECT
    offer_id,
    source_id,
    supplier_id,
    external_id,
    url,
    normalized_name AS name,
    normalized_key AS merge_key,
    brand,
    article,
    item_type,
    okpd2_code,
    okpd2_level,
    rubric,
    rubric_name,
    normalized_attributes AS attributes,
    unit_code,
    unit_name,
    price,
    currency,
    price_per_unit,
    price_unit_code,
    availability,
    delivery_regions,
    supplier_role,
    seller_status,
    classification_method AS method,
    classification_confidence AS confidence,
    classification_evidence AS evidence,
    normalizer_version,
    classifier_version,
    first_seen_at,
    last_seen_at,
    updated_at
FROM supplier_search.offers_current;
