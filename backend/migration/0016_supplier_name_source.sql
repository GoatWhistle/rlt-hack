-- Происхождение названия компании: карточка источника или реестр МСП по точному ИНН.
ALTER TABLE supplier_search.suppliers
    ADD COLUMN IF NOT EXISTS name_source Enum8('source' = 0, 'registry' = 1) DEFAULT 'source';

CREATE OR REPLACE VIEW supplier_search.suppliers_current AS
SELECT * FROM supplier_search.suppliers FINAL WHERE is_deleted = 0;
