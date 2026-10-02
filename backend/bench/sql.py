from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from bench.vocabulary import (
    CATEGORIES,
    COMPANY_FORMS,
    COMPANY_ROOTS,
    COMPANY_TAILS,
    CUSTOMERS,
    REGIONS,
)

DB = "supplier_search"
SUPPLIER_KIND = 1
OFFER_KIND = 2
SOURCE_KIND = 3
CATALOG_KIND = 4
ITEM_KIND = 5
CATEGORY_COUNT = len(CATEGORIES)


@dataclass(frozen=True, slots=True)
class Volume:
    suppliers: int = 50_000
    sources: int = 300
    offers: int = 300_000
    lots: int = 100_000
    items: int = 300_000
    participants_per_lot: int = 3


REAL_VOLUME = Volume(
    offers=1_000_000,
    lots=604_452,
    items=2_971_651,
    participants_per_lot=2,
)
VOLUMES = {"default": Volume(), "real": REAL_VOLUME}


def quote(text: str) -> str:
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def strings(values: Iterable[str]) -> str:
    return "[" + ", ".join(quote(value) for value in values) + "]"


def integers(values: Iterable[int]) -> str:
    return "[" + ", ".join(str(value) for value in values) + "]"


def uuid(kind: int, expression: str) -> str:
    suffix = f"leftPad(lower(hex(toUInt64({expression}))), 12, '0')"
    return f"toUUID(concat('{kind:08x}-0000-4000-8000-', {suffix}))"


def _flat(name: str, groups: Sequence[Sequence[str]]) -> list[str]:
    offsets: list[int] = []
    total = 0
    for group in groups:
        offsets.append(total)
        total += len(group)
    values = [value for group in groups for value in group]
    return [
        f"{strings(values)} AS {name}",
        f"{integers(offsets)} AS {name}_offsets",
        f"{integers(len(group) for group in groups)} AS {name}_sizes",
    ]


def constants() -> str:
    product_category = [
        index for index, category in enumerate(CATEGORIES) for _ in category.products
    ]
    parts = [
        *_flat("products", [category.products for category in CATEGORIES]),
        *_flat("attributes", [category.attributes for category in CATEGORIES]),
        *_flat("brands", [category.brands for category in CATEGORIES]),
        f"{integers(product_category)} AS product_category",
        f"{strings(category.name for category in CATEGORIES)} AS category_names",
        f"{strings(category.okpd2 for category in CATEGORIES)} AS okpd2_codes",
        f"{strings(category.item_type for category in CATEGORIES)} AS item_types",
        f"{strings(category.unit for category in CATEGORIES)} AS units",
        f"{strings(REGIONS)} AS regions",
        f"{strings(COMPANY_FORMS)} AS forms",
        f"{strings(COMPANY_ROOTS)} AS roots",
        f"{strings(COMPANY_TAILS)} AS tails",
        f"{strings(CUSTOMERS)} AS customers",
    ]
    return ",\n".join(parts)


def within(name: str, category: str, seed: str) -> str:
    return f"{name}_offsets[{category} + 1] + ({seed}) % {name}_sizes[{category} + 1]"


def pick_within(name: str, category: str, seed: str) -> str:
    return f"{name}[{within(name, category, seed)} + 1]"


def supplier_roll(supplier: str) -> str:
    return f"cityHash64({supplier}, 11) % 100"


def supplier_inn(supplier: str) -> str:
    roll = supplier_roll(supplier)
    own = f"if({roll} < 4 AND {supplier} > 0, {supplier} - 1, {supplier})"
    return f"if({roll} BETWEEN 4 AND 11, NULL, toString(7700000000 + {own}))"


def supplier_region(supplier: str) -> str:
    return f"regions[1 + cityHash64({supplier}, 14) % length(regions)]"


def supplier_category(supplier: str, seed: str) -> str:
    second = f"cityHash64({supplier}, 13) % {CATEGORY_COUNT}"
    return f"if(({seed}) % 10 < 3, {second}, {supplier} % {CATEGORY_COUNT})"


def lot_category(lot: str) -> str:
    return f"cityHash64({lot}, 31) % {CATEGORY_COUNT}"


def lot_id(lot: str) -> str:
    return f"toString(1000000 + {lot})"
