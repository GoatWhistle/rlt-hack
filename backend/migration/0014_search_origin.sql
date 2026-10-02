-- Происхождение поиска: ручной запрос или лот загруженного CSV.
-- Лоты CSV хранятся в общем архиве, но не попадают в список недавних поисков.
ALTER TABLE supplier_search.searches
    ADD COLUMN IF NOT EXISTS origin LowCardinality(String) DEFAULT 'manual' AFTER items;

ALTER TABLE supplier_search.searches
    ADD CONSTRAINT IF NOT EXISTS valid_origin CHECK origin IN ('manual', 'upload');

DROP VIEW IF EXISTS supplier_search.searches_current;

CREATE VIEW IF NOT EXISTS supplier_search.searches_current AS
SELECT * FROM supplier_search.searches FINAL WHERE is_deleted = 0;
