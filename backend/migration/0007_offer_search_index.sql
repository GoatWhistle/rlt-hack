ALTER TABLE supplier_search.offers
    ADD COLUMN IF NOT EXISTS search_text String DEFAULT replaceAll(lowerUTF8(concat(name, ' ', brand, ' ', article, ' ', source_category, ' ', substringUTF8(description, 1, 500))), 'ё', 'е');

ALTER TABLE supplier_search.offers MATERIALIZE COLUMN search_text;

ALTER TABLE supplier_search.offers
    ADD INDEX IF NOT EXISTS idx_offers_search_tokens search_text TYPE tokenbf_v1(32768, 3, 0) GRANULARITY 4;

ALTER TABLE supplier_search.offers
    ADD INDEX IF NOT EXISTS idx_offers_search_ngrams search_text TYPE ngrambf_v1(4, 65536, 3, 0) GRANULARITY 4;

ALTER TABLE supplier_search.offers
    ADD INDEX IF NOT EXISTS idx_offers_supplier supplier_id TYPE bloom_filter GRANULARITY 4;

ALTER TABLE supplier_search.offers MATERIALIZE INDEX idx_offers_search_tokens;

ALTER TABLE supplier_search.offers MATERIALIZE INDEX idx_offers_search_ngrams;

ALTER TABLE supplier_search.offers MATERIALIZE INDEX idx_offers_supplier;

DROP VIEW IF EXISTS supplier_search.offers_current;

CREATE VIEW supplier_search.offers_current AS
SELECT * FROM supplier_search.offers FINAL WHERE is_deleted = 0;
