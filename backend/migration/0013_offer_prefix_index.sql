ALTER TABLE supplier_search.offers DROP INDEX IF EXISTS idx_offers_search_tokens;

ALTER TABLE supplier_search.offers DROP INDEX IF EXISTS idx_offers_search_ngrams;

ALTER TABLE supplier_search.offers
    ADD COLUMN IF NOT EXISTS search_terms UInt16 DEFAULT toUInt16(least(65535, length(arrayFilter(t -> t != '', splitByRegexp('[^0-9a-zа-я]+', search_text)))));

ALTER TABLE supplier_search.offers MATERIALIZE COLUMN search_terms SETTINGS mutations_sync = 2;

ALTER TABLE supplier_search.offers
    ADD INDEX IF NOT EXISTS idx_offers_search_prefixes arrayDistinct(arrayFlatten(arrayMap(t -> [leftUTF8(t, 3), leftUTF8(t, 4), leftUTF8(t, 5), leftUTF8(t, 6)], arrayFilter(t -> lengthUTF8(t) >= 3, splitByRegexp('[^0-9a-zа-я]+', search_text))))) TYPE text(tokenizer = array);

ALTER TABLE supplier_search.offers MATERIALIZE INDEX idx_offers_search_prefixes SETTINGS mutations_sync = 2;

CREATE OR REPLACE VIEW supplier_search.offers_current AS
SELECT * FROM supplier_search.offers FINAL WHERE is_deleted = 0;
