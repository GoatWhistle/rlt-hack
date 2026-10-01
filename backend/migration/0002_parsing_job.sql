-- Миграция 0002: состояние инкрементального обхода для джобы парсинга.
-- Очередь заданий и блокировки worker в ClickHouse не хранятся: таблицы ниже
-- описывают только достигнутую позицию обхода и валидаторы HTTP-кеша.

CREATE TABLE IF NOT EXISTS supplier_search.crawl_cursors
(
    source_id UUID,
    cursor_key String, -- Раздел состояния внутри источника: 'catalog', 'sitemap', 'feed'.
    position String, -- Значение назначает парсер; схема его не интерпретирует.
    http_etag String,
    http_last_modified String,
    last_run_id UUID,
    last_success_at DateTime64(3, 'UTC'),
    is_complete UInt8 DEFAULT 0, -- 1 только после полного успешного обхода раздела.
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64,
    is_deleted UInt8 DEFAULT 0,
    CONSTRAINT valid_version CHECK version > 0,
    CONSTRAINT valid_flags CHECK is_complete IN (0, 1) AND is_deleted IN (0, 1)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (source_id, cursor_key);

CREATE VIEW IF NOT EXISTS supplier_search.crawl_cursors_current AS
SELECT * FROM supplier_search.crawl_cursors FINAL WHERE is_deleted = 0;

-- Предложения упорядочены по offer_id: отбор по источнику нужен джобе,
-- чтобы снимать с продажи позиции, не найденные при полном обходе.
ALTER TABLE supplier_search.offers
    ADD INDEX IF NOT EXISTS idx_offers_source source_id TYPE bloom_filter GRANULARITY 4;

-- Наблюдения упорядочены по времени: отбор по обходу нужен для разбора ошибок.
ALTER TABLE supplier_search.observations
    ADD INDEX IF NOT EXISTS idx_observations_run run_id TYPE bloom_filter GRANULARITY 4;

-- Параметры парсера источника: адрес фида, разделы каталога, лимиты страниц.
-- Хранятся вместе с источником, чтобы джоба не требовала отдельной конфигурации.
ALTER TABLE supplier_search.sources
    ADD COLUMN IF NOT EXISTS options Map(String, String);

-- Представление запоминает список колонок при создании: после ALTER его нужно
-- пересоздать, иначе новая колонка в `*_current` не видна. Это правило
-- относится к любой будущей миграции, добавляющей колонки.
DROP VIEW IF EXISTS supplier_search.sources_current;

CREATE VIEW supplier_search.sources_current AS
SELECT * FROM supplier_search.sources FINAL WHERE is_deleted = 0;
