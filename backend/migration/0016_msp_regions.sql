ALTER TABLE supplier_search.msp_companies
    ADD COLUMN IF NOT EXISTS region LowCardinality(String),
    ADD COLUMN IF NOT EXISTS region_name String;
