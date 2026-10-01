from bench.sql import (
    CATEGORY_COUNT,
    DB,
    ITEM_KIND,
    SUPPLIER_KIND,
    Volume,
    constants,
    lot_category,
    lot_id,
    pick_within,
    supplier_inn,
    uuid,
    within,
)

LOTS = """
INSERT INTO {db}.procurement_lots (lot_id, procedure_id, reqnum, procedure_name, subject,
    start_price, is_smp, customer_inn, customer_kpp, platform, version)
WITH {constants},
    cityHash64(number, 32) AS h,
    {category} AS category,
    {product} AS product
SELECT {lot_id}, toString(500000 + intDiv(number, 2)), concat('32', toString(1000000000 + number)),
    concat('Поставка: ', lowerUTF8(category_names[category + 1])),
    concat(products[product + 1], ' для нужд ', customers[1 + intDiv(h, 11) % length(customers)]),
    toDecimal64(1000 + (h % 100000000) / 10, 2), h % 2,
    toString(7800000000 + h % 100000), '780001001',
    ['РТС-тендер', 'Сбербанк-АСТ', 'ЕЭТП', 'Росэлторг'][1 + intDiv(h, 3) % 4], 1
FROM numbers({count})
"""

ITEMS = """
INSERT INTO {db}.procurement_items (procurement_item_id, lot_id, source_row_key, product_name,
    okpd2_code, item_type, quantity, unit, match_status, version)
WITH {constants},
    cityHash64(number, 41) AS h,
    h % {lots} AS lot,
    {category} AS category,
    {product} AS product,
    {attribute} AS attribute
SELECT {item_id}, {lot_id}, toString(number), concat(products[product + 1], ' ', attribute),
    okpd2_codes[category + 1], item_types[category + 1],
    toDecimal64(1 + intDiv(h, 13) % 1000, 4), units[category + 1], 'unmatched', 1
FROM numbers({count})
"""

PARTICIPATIONS = """
INSERT INTO {db}.lot_participations (lot_id, supplier_inn, supplier_kpp, supplier_id,
    is_winner, version)
WITH intDiv(number, {per_lot}) AS lot,
    number % {per_lot} AS seat,
    {category} AS category,
    category + {categories} * (cityHash64(lot, seat, 51) % {slots}) AS supplier
SELECT {lot_id}, ifNull({inn}, ''), '', {supplier_id},
    if(seat = cityHash64(lot, 52) % {per_lot}, 1, 0), 1
FROM numbers({count})
"""


def lots(volume: Volume) -> str:
    return LOTS.format(
        db=DB,
        constants=constants(),
        category=lot_category("number"),
        product=within("products", "category", "intDiv(h, 7)"),
        lot_id=lot_id("number"),
        count=volume.lots,
    )


def items(volume: Volume) -> str:
    return ITEMS.format(
        db=DB,
        constants=constants(),
        lots=volume.lots,
        category=lot_category("lot"),
        product=within("products", "category", "intDiv(h, 7)"),
        attribute=pick_within("attributes", "category", "intDiv(h, 7919)"),
        item_id=uuid(ITEM_KIND, "number"),
        lot_id=lot_id("lot"),
        count=volume.items,
    )


def participations(volume: Volume) -> str:
    return PARTICIPATIONS.format(
        db=DB,
        per_lot=volume.participants_per_lot,
        category=lot_category("lot"),
        categories=CATEGORY_COUNT,
        slots=volume.suppliers // CATEGORY_COUNT,
        lot_id=lot_id("lot"),
        inn=supplier_inn("supplier"),
        supplier_id=uuid(SUPPLIER_KIND, "supplier"),
        count=volume.lots * volume.participants_per_lot,
    )
