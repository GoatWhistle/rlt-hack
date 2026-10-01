-- Миграция 0006: чистка полей, которые никто не заполняет, и единый ключ
-- идентичности предложения.
--
-- Убираются:
--   suppliers.legal_status      — ни один адаптер его не присваивал; правовую
--                                 форму даёт реестр вместе с ОКВЭД;
--   sources.enabled             — включение источника живёт в переменных
--                                 окружения, второе место хранения расходится;
--   offers.delivery_regions     — заполнялось только параметром адаптера фида,
--                                 который никто не передавал; регион поставки
--                                 берётся у компании;
--   offers.role_evidence_url    — проверено на данных: ни одного значения,
--                                 которого нет в url или в соседнем поле.
--
-- seller_evidence_url переименован в evidence_url: это единственный адрес, где
-- подтверждается, что продавец — именно эта компания.
--
-- Представления с SELECT * фиксируют список колонок при создании, поэтому
-- каждое затронутое пересоздаётся.
ALTER TABLE supplier_search.suppliers DROP COLUMN IF EXISTS legal_status;

-- Ограничение снимается раньше колонки: оно на неё ссылается.
ALTER TABLE supplier_search.sources DROP CONSTRAINT IF EXISTS valid_flags;

ALTER TABLE supplier_search.sources DROP COLUMN IF EXISTS enabled;

ALTER TABLE supplier_search.sources ADD CONSTRAINT IF NOT EXISTS valid_deleted
    CHECK is_deleted IN (0, 1);

ALTER TABLE supplier_search.offers DROP COLUMN IF EXISTS delivery_regions;

ALTER TABLE supplier_search.offers DROP COLUMN IF EXISTS role_evidence_url;

ALTER TABLE supplier_search.offers DROP CONSTRAINT IF EXISTS valid_seller;

ALTER TABLE supplier_search.offers RENAME COLUMN IF EXISTS seller_evidence_url TO evidence_url;

ALTER TABLE supplier_search.offers ADD CONSTRAINT IF NOT EXISTS valid_seller
    CHECK seller_status != 'verified' OR isNotNull(supplier_id);

CREATE OR REPLACE VIEW supplier_search.suppliers_current AS
SELECT * FROM supplier_search.suppliers FINAL WHERE is_deleted = 0;

CREATE OR REPLACE VIEW supplier_search.sources_current AS
SELECT * FROM supplier_search.sources FINAL WHERE is_deleted = 0;

CREATE OR REPLACE VIEW supplier_search.offers_current AS
SELECT * FROM supplier_search.offers FINAL WHERE is_deleted = 0;

-- Описание товара в представление добавлено: это единственный текст источника
-- сверх названия, и он нужен поиску.
CREATE OR REPLACE VIEW supplier_search.offers_normalized AS
SELECT
    offer_id,
    source_id,
    supplier_id,
    external_id,
    url,
    normalized_name AS name,
    description,
    normalized_key AS merge_key,
    brand,
    article,
    item_type,
    okpd2_code,
    okpd2_level,
    rubric,
    rubric_name,
    normalized_attributes AS attributes,
    unit_code,
    unit_name,
    price,
    currency,
    price_per_unit,
    price_unit_code,
    availability,
    supplier_role,
    seller_status,
    evidence_url,
    role_evidence_text,
    classification_method AS method,
    classification_confidence AS confidence,
    classification_evidence AS evidence,
    normalizer_version,
    classifier_version,
    first_seen_at,
    last_seen_at,
    updated_at
FROM supplier_search.offers_current;
