ALTER TABLE supplier_search.moscow_products
ADD COLUMN IF NOT EXISTS detail_status LowCardinality(String) DEFAULT 'summary_only';

DROP VIEW IF EXISTS supplier_search.moscow_products_current;

CREATE VIEW supplier_search.moscow_products_current AS
SELECT * FROM supplier_search.moscow_products
WHERE run_id = (
    SELECT run_id FROM supplier_search.moscow_product_publications
    ORDER BY completed_at DESC, run_id DESC LIMIT 1
);
