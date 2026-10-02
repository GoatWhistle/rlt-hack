from decimal import Decimal

import pytest

from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from src.adapter.text.rule_interpreter.interpreter import RuleQueryInterpreter
from src.adapter.text.rule_interpreter.okpd2 import extract_okpd2
from src.adapter.text.rule_interpreter.quantity import canonical_unit, extract_quantity
from src.adapter.text.rule_interpreter.splitter import split_positions
from src.models.enums import ItemOrigin, ItemType
from src.models.search.query_item import Quantity
from src.models.search.search import SearchFilters, SearchQuery, SearchText


def query(text: str, item_type: ItemType | None = None) -> SearchQuery:
    return SearchQuery(SearchText(text), filters=SearchFilters(item_type=item_type))


async def interpret(text: str, item_type: ItemType | None = None) -> list[tuple[object, ...]]:
    items = await RuleQueryInterpreter(RussianAnalyzer()).interpret(query(text, item_type))
    return [(item.item_id, item.name, item.okpd2, item.quantity) for item in items]


async def test_positions_split_on_commas_after_quantities() -> None:
    text = "Крупа гречневая ядрица 500 кг, рис шлифованный 200 кг, доставка в Санкт-Петербург"
    assert await interpret(text) == [
        ("i1", "Крупа гречневая ядрица", "", Quantity(Decimal(500), "кг")),
        ("i2", "Рис шлифованный", "", Quantity(Decimal(200), "кг")),
    ]


async def test_positions_split_on_semicolons_markers_and_and() -> None:
    assert [row[1] for row in await interpret("бумага; ручки; скрепки")] == [
        "Бумага",
        "Ручки",
        "Скрепки",
    ]
    numbered = await interpret("1. Бумага А4 80 г/м2 500 листов 2) Ручка синяя 100 шт")
    assert numbered == [
        ("i1", "Бумага А4 80 г/м2", "", Quantity(Decimal(500), "лист")),
        ("i2", "Ручка синяя", "", Quantity(Decimal(100), "шт")),
    ]
    dashed = await interpret("- кабель ВВГ 3x2.5 100 м - розетка 20 шт и вилка 5 шт")
    assert [(row[1], row[3]) for row in dashed] == [
        ("Кабель ВВГ 3x2.5", Quantity(Decimal(100), "м")),
        ("Розетка", Quantity(Decimal(20), "шт")),
        ("Вилка", Quantity(Decimal(5), "шт")),
    ]


async def test_okpd2_code_moves_out_of_the_name() -> None:
    rows = await interpret("Сахар-песок ОКПД2 10.81.12.110 1,5 т")
    assert rows == [("i1", "Сахар-песок", "10.81.12.110", Quantity(Decimal("1.5"), "т"))]


async def test_whole_text_is_one_item_when_splitting_finds_nothing() -> None:
    rows = await interpret("доставка песка 5 т")
    assert rows == [("i1", "Доставка песка", "", Quantity(Decimal(5), "т"))]


async def test_text_without_meaningful_words_gives_no_items() -> None:
    assert await interpret("и в на; с по") == []


async def test_items_take_origin_and_type_from_the_query() -> None:
    interpreter = RuleQueryInterpreter(RussianAnalyzer(), max_items=2)
    items = await interpreter.interpret(query("а1 б2; в3 г4; д5 е6", ItemType.GOODS))
    assert [item.item_id for item in items] == ["i1", "i2"]
    assert {(item.origin, item.item_type) for item in items} == {(ItemOrigin.TEXT, ItemType.GOODS)}
    untyped = await interpreter.interpret(query("цемент"))
    assert untyped[0].item_type == ItemType.UNKNOWN


@pytest.mark.parametrize(
    ("raw", "unit"),
    [
        ("кв.м", "м2"),
        ("м³", "м3"),
        ("тонны", "т"),
        ("штук", "шт"),
        ("литров", "л"),
        ("упаковки", "упак"),
        ("пачек", "пачка"),
        ("рулонов", "рулон"),
        ("к-т", "компл"),
        ("коробок", "коробка"),
        ("пары", "пара"),
        ("мешков", "мешок"),
        ("бут.", "бутылка"),
        ("гр", "г"),
        ("мл", "мл"),
        ("км", "км"),
        ("КГ", "кг"),
    ],
)
def test_units_are_canonical(raw: str, unit: str) -> None:
    assert canonical_unit(raw) == unit


def test_quantity_ignores_codes_dimensions_and_zero() -> None:
    assert extract_quantity("бумага 80 г/м2")[0] is None
    assert extract_quantity("лист 0 шт")[0] is None
    quantity, rest = extract_quantity("молоко 1 000 л")
    assert quantity == Quantity(Decimal(1000), "л")
    assert rest.strip() == "молоко"
    assert extract_quantity("А4 листы")[0] is None


def test_okpd2_and_splitter_edge_cases() -> None:
    assert extract_okpd2("без кода") == ("", "без кода")
    assert extract_okpd2("код 17.12 и 10.81.12")[0] == "17.12"
    assert split_positions("  ;  ") == []
    assert split_positions("гвозди 5 кг,") == ["гвозди 5 кг,"]
