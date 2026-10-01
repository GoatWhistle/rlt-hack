-- Сохранять поля полного пакета поставщиков после очистки схемы соседних джоб.
ALTER TABLE supplier_search.sources
    ADD COLUMN IF NOT EXISTS enabled UInt8 DEFAULT 1;

ALTER TABLE supplier_search.suppliers
    ADD COLUMN IF NOT EXISTS legal_status LowCardinality(String) DEFAULT 'unknown';

ALTER TABLE supplier_search.offers
    ADD COLUMN IF NOT EXISTS seller_evidence_url String DEFAULT '';

ALTER TABLE supplier_search.offers
    ADD COLUMN IF NOT EXISTS delivery_regions Array(String) DEFAULT [];

ALTER TABLE supplier_search.offers
    ADD COLUMN IF NOT EXISTS role_evidence_url String DEFAULT '';

DROP VIEW IF EXISTS supplier_search.sources_current;

CREATE VIEW supplier_search.sources_current AS
SELECT * FROM supplier_search.sources FINAL WHERE is_deleted = 0;

DROP VIEW IF EXISTS supplier_search.suppliers_current;

CREATE VIEW supplier_search.suppliers_current AS
SELECT * FROM supplier_search.suppliers FINAL WHERE is_deleted = 0;

DROP VIEW IF EXISTS supplier_search.offers_current;

CREATE VIEW supplier_search.offers_current AS
SELECT * FROM supplier_search.offers FINAL WHERE is_deleted = 0;
