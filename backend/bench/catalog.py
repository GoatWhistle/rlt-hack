from bench.sql import (
    CATALOG_KIND,
    DB,
    OFFER_KIND,
    SOURCE_KIND,
    SUPPLIER_KIND,
    Volume,
    constants,
    pick_within,
    supplier_category,
    supplier_inn,
    supplier_region,
    supplier_roll,
    uuid,
    within,
)

SUPPLIERS = """
INSERT INTO {db}.suppliers (supplier_id, inn, name, region, website,
    identity_status, identity_evidence_url, version)
WITH {constants},
    cityHash64(number, 12) AS h,
    {roll} AS roll,
    {inn} AS inn_value
SELECT {supplier_id}, inn_value,
    concat(forms[1 + h % length(forms)], ' «', roots[1 + intDiv(h, 7) % length(roots)],
        tails[1 + intDiv(h, 97) % length(tails)], '»'),
    {region},
    if(h % 3 = 0, '', concat('https://supplier-', toString(number), '.example.ru')),
    multiIf(isNull(inn_value), 'unverified', roll < 4, 'conflict', roll < 70, 'verified',
        'unverified'),
    if(roll BETWEEN 12 AND 69, concat('https://egrul.example.ru/', toString(number)), ''),
    1
FROM numbers({count})
"""

SOURCES = """
INSERT INTO {db}.sources (source_id, name, base_url, source_type, supplier_id,
    ownership_status, ownership_evidence_url, provider_name, version)
SELECT {source_id}, concat('Каталог ', toString(number)),
    concat('https://shop-', toString(number), '.example.ru/'),
    ['directory', 'website', 'feed', 'price_list'][1 + number % 4],
    NULL, 'unverified', '', 'bench', 1
FROM numbers({count})
"""

OFFER_SCOPE = """
WITH {constants},
    cityHash64(number, 21) AS h,
    toUInt64({suppliers} * pow((h % 1000003) / 1000003, 1.6)) AS supplier,
    {category} AS category,
    {product} AS product,
    {attribute} AS attribute,
    {brand} AS brand,
    supplier % {sources} AS source
"""

OFFERS = """
INSERT INTO {db}.offers (offer_id, source_id, external_id, supplier_id, seller_status, url,
    name, description, item_type, brand, article, source_category, okpd2_code, price,
    currency, unit, availability, supplier_role, content_hash,
    first_seen_at, last_seen_at, version)
{scope}
SELECT {offer_id}, {source_id}, toString(number), {supplier_id},
    if(h % 2 = 0, 'verified', 'unverified'),
    concat('https://shop-', toString(source), '.example.ru/p/', toString(number)),
    trimBoth(concat(products[product + 1], ' ', attribute, ' ', brand)),
    concat(products[product + 1], '. ', category_names[category + 1], '. Доставка: ',
        {region}),
    item_types[category + 1], brand, upper(substring(hex(h), 1, 8)),
    category_names[category + 1], okpd2_codes[category + 1],
    if(intDiv(h, 5) % 5 = 0, NULL, toDecimal64(10 + (h % 5000000) / 100, 4)),
    'RUB', units[category + 1],
    multiIf(h % 100 < 4, 'unavailable', h % 100 < 10, 'on_order', 'available'),
    if(item_types[category + 1] = 'service', 'service_provider',
        ['manufacturer', 'distributor', 'reseller', 'unknown'][1 + intDiv(h, 3) % 4]),
    lower(hex(h)),
    now64(3) - toIntervalHour(h % 720) - toIntervalDay(intDiv(h, 9) % 365),
    now64(3) - toIntervalHour(h % 720),
    1
FROM numbers({count})
"""

CATALOG_ITEMS = """
INSERT INTO {db}.catalog_items (catalog_item_id, name, item_type, okpd2_codes, status, version)
WITH {constants}
SELECT {catalog_id}, products[number + 1], item_types[product_category[number + 1] + 1],
    [okpd2_codes[product_category[number + 1] + 1]], 'confirmed', 1
FROM numbers(length(products))
"""

OFFER_MATCHES = """
INSERT INTO {db}.offer_matches (offer_id, catalog_item_id, status, confidence, method,
    algorithm_version, offer_content_hash, version)
{scope}
SELECT {offer_id}, {catalog_id},
    if(intDiv(h, 7) % 10 < 7, 'accepted', 'review'),
    0.5 + (h % 500) / 1000, 'bench', 'bench-1', lower(hex(h)), 1
FROM numbers({count})
WHERE intDiv(h, 17) % 10 < 6
"""


def suppliers(volume: Volume) -> str:
    return SUPPLIERS.format(
        db=DB,
        constants=constants(),
        roll=supplier_roll("number"),
        inn=supplier_inn("number"),
        supplier_id=uuid(SUPPLIER_KIND, "number"),
        region=supplier_region("number"),
        count=volume.suppliers,
    )


def sources(volume: Volume) -> str:
    return SOURCES.format(db=DB, source_id=uuid(SOURCE_KIND, "number"), count=volume.sources)


def _offer_scope(volume: Volume) -> str:
    return OFFER_SCOPE.format(
        constants=constants(),
        suppliers=volume.suppliers,
        category=supplier_category("supplier", "intDiv(h, 13)"),
        product=within("products", "category", "intDiv(h, 101)"),
        attribute=pick_within("attributes", "category", "intDiv(h, 7919)"),
        brand=pick_within("brands", "category", "intDiv(h, 104729)"),
        sources=volume.sources,
    )


def offers(volume: Volume) -> str:
    return OFFERS.format(
        db=DB,
        scope=_offer_scope(volume),
        offer_id=uuid(OFFER_KIND, "number"),
        source_id=uuid(SOURCE_KIND, "source"),
        supplier_id=uuid(SUPPLIER_KIND, "supplier"),
        region=supplier_region("supplier"),
        count=volume.offers,
    )


def catalog_items() -> str:
    return CATALOG_ITEMS.format(
        db=DB, constants=constants(), catalog_id=uuid(CATALOG_KIND, "number")
    )


def offer_matches(volume: Volume) -> str:
    return OFFER_MATCHES.format(
        db=DB,
        scope=_offer_scope(volume),
        offer_id=uuid(OFFER_KIND, "number"),
        catalog_id=uuid(CATALOG_KIND, "product"),
        count=volume.offers,
    )
