from datetime import date

from rlt_ml.cards import _group_examples, _unique_products, compact_profile


def test_compact_profile_puts_diverse_products_before_examples():
    rows = [
        {"query_excerpt": "Текущая закупка 1", "product_items": [
            {"name": "Сервер X", "code": "26.20.14.000"},
            {"name": "Монитор 24", "code": "26.20.17.110"},
        ]},
        {"query_excerpt": "Текущая закупка 2", "product_items": [
            {"name": "сервер x", "code": "26.20.14.000"},
            {"name": "Кабель USB", "code": "27.32.13.190"},
        ]},
    ]
    text, products = compact_profile("26.20", rows, product_limit=3)
    assert [row["name"] for row in products] == ["Сервер X", "Монитор 24", "Кабель USB"]
    assert text.index("Товары и услуги:") < text.index("Примеры закупок:")


def test_product_selection_is_deterministic_and_casefold_deduplicated():
    products = [{"name": "Модель A"}, {"name": "модель a"}, {"name": "Артикул-42"}]
    examples = [{"product_items": products}]
    assert [row["name"] for row in _unique_products(examples, 10)] == [
        "Модель A", "Артикул-42"
    ]
    assert _unique_products(examples, 1) == [products[0]]


def test_okpd2_groups_rank_and_keep_distinct_examples():
    examples = [
        {"product_items": [{"name": "A", "code": "26.20.11.000"}],
         "last_date": date(2024, 1, 1),
         "profile_description": "a", "lot_count": 2},
        {"product_items": [{"name": "B", "code": "26.20.12.000"}],
         "last_date": date(2024, 2, 1),
         "profile_description": "b", "lot_count": 1},
    ]
    groups = _group_examples(examples)
    assert groups[0]["label"] == "26.20.11"
    assert groups[0]["distinct_lots"] == 2
    assert groups[1]["label"] == "26.20.12"
