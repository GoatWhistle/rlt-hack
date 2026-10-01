-- Миграция 0003: обход источников адаптерами-провайдерами.
-- Адаптер источника сам знает свои адреса и разметку, отдаёт пакет с готовыми
-- компаниями и предложениями и включается флагом развёртывания. Из схемы уходит
-- всё, что обслуживало настраиваемый парсер: параметры источника, позиции
-- инкрементального обхода и снимки отдельных документов.

ALTER TABLE supplier_search.sources DROP COLUMN IF EXISTS options;

ALTER TABLE supplier_search.sources RENAME COLUMN IF EXISTS parser_name TO provider_name;

-- Представление запоминает список колонок при создании: после ALTER его нужно
-- пересоздать, иначе изменения в `*_current` не видны.
DROP VIEW IF EXISTS supplier_search.sources_current;

CREATE VIEW supplier_search.sources_current AS
SELECT * FROM supplier_search.sources FINAL WHERE is_deleted = 0;

-- Свидетельство предложения — его собственный адрес и подтверждающий текст:
-- ссылки на снимок документа у предложения больше нет.
ALTER TABLE supplier_search.offers DROP COLUMN IF EXISTS observation_id;

DROP VIEW IF EXISTS supplier_search.offers_current;

CREATE VIEW supplier_search.offers_current AS
SELECT * FROM supplier_search.offers FINAL WHERE is_deleted = 0;

-- Журнал обхода: пакет источника приходит целиком, поэтому признак полного
-- каталога и число страниц заменяются числом собранных компаний.
ALTER TABLE supplier_search.crawl_runs DROP CONSTRAINT IF EXISTS valid_full;

ALTER TABLE supplier_search.crawl_runs DROP COLUMN IF EXISTS is_full_catalog;

ALTER TABLE supplier_search.crawl_runs RENAME COLUMN IF EXISTS pages_fetched TO suppliers_extracted;

ALTER TABLE supplier_search.crawl_runs RENAME COLUMN IF EXISTS parser_version TO provider_name;

-- Снимки документов и позиции инкрементального обхода не ведутся.
DROP TABLE IF EXISTS supplier_search.observations;

DROP VIEW IF EXISTS supplier_search.crawl_cursors_current;

DROP TABLE IF EXISTS supplier_search.crawl_cursors;
