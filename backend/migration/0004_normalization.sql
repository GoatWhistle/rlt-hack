-- Миграция 0004: производные значения нормализации и классификации.
-- Исходные поля предложения не меняются: нормализованное название, единица,
-- цена за базовую единицу, код ОКПД2 и рубрика лежат рядом отдельными
-- колонками. Версия алгоритма хранится вместе со значением: по ней видно,
-- какие строки пересчитывать после изменения правил.
-- Представление offers_current пересоздаётся: список колонок у вьюхи с SELECT *
-- фиксируется при создании и сам новые колонки не подхватывает.
ALTER TABLE supplier_search.offers
    ADD COLUMN IF NOT EXISTS normalized_name String,
    ADD COLUMN IF NOT EXISTS normalized_key String,
    ADD COLUMN IF NOT EXISTS normalized_attributes Map(String, String),
    ADD COLUMN IF NOT EXISTS unit_code LowCardinality(String),
    ADD COLUMN IF NOT EXISTS price_per_unit Nullable(Decimal(18, 4)),
    ADD COLUMN IF NOT EXISTS price_unit_code LowCardinality(String),
    ADD COLUMN IF NOT EXISTS normalizer_version String,
    ADD COLUMN IF NOT EXISTS okpd2_level UInt8 DEFAULT 0,
    ADD COLUMN IF NOT EXISTS rubric LowCardinality(String),
    ADD COLUMN IF NOT EXISTS classification_method LowCardinality(String) DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS classification_confidence Float32 DEFAULT 0,
    ADD COLUMN IF NOT EXISTS classification_evidence String,
    ADD COLUMN IF NOT EXISTS classifier_version String;

ALTER TABLE supplier_search.offers
    ADD CONSTRAINT IF NOT EXISTS valid_confidence
    CHECK isFinite(classification_confidence)
      AND classification_confidence >= 0 AND classification_confidence <= 1;

ALTER TABLE supplier_search.offers
    ADD CONSTRAINT IF NOT EXISTS valid_okpd2_level CHECK okpd2_level <= 10;

CREATE OR REPLACE VIEW supplier_search.offers_current AS
SELECT * FROM supplier_search.offers FINAL WHERE is_deleted = 0;
