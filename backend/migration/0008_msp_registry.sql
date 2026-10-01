-- Миграция 0008: реестр субъектов МСП ФНС и роль компании.
--
-- msp_companies — сведения выгрузки реестра, по строке на ИНН. Новая выгрузка
-- заменяет строку той же компании, а компании, выбывшие из реестра, удаляются
-- после полной загрузки по дате формирования сведений.
--
-- У компании появляется роль на рынке и её основание: их проставляет
-- обогащение по реестру сразу после обхода источника.
CREATE TABLE IF NOT EXISTS supplier_search.msp_companies
(
    inn String,
    name String,
    registry_date Date,
    okved_main LowCardinality(String),
    okved_main_name String,
    -- 1, если основного кода в сведениях реестра нет и он взят из отчётности.
    okved_main_reported UInt8,
    okved_extra Array(LowCardinality(String)),
    products Array(String),
    loaded_at DateTime64(3, 'UTC') DEFAULT now64(3),
    CONSTRAINT valid_inn CHECK match(inn, '^([0-9]{10}|[0-9]{12})$')
)
ENGINE = ReplacingMergeTree(registry_date)
ORDER BY inn;

ALTER TABLE supplier_search.suppliers
    ADD COLUMN IF NOT EXISTS role Enum8('unknown' = 0, 'manufacturer' = 1, 'distributor' = 2, 'reseller' = 3, 'service_provider' = 4),
    ADD COLUMN IF NOT EXISTS role_evidence String;

CREATE OR REPLACE VIEW supplier_search.suppliers_current AS
SELECT * FROM supplier_search.suppliers FINAL WHERE is_deleted = 0;
