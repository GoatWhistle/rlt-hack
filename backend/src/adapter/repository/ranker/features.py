"""Observable retrieval and historical features; no target-lot products."""

import math
import re
from datetime import date

FEATURES = (
    "dense_score",
    "bm25_score",
    "rrf_score",
    "dense_rank",
    "bm25_rank",
    "customer_rank",
    "token_coverage",
    "supplier_participations",
    "supplier_wins",
    "supplier_win_rate",
    "category_participations",
    "category_wins",
    "category_win_rate",
    "customer_participations",
    "customer_wins",
    "customer_win_rate",
    "profile_examples",
    "profile_age",
    "price_distance",
    "missing_customer",
    "missing_price",
    "card_count",
)
STOP = frozenset(
    [
        "поставка",
        "поставку",
        "поставки",
        "оказание",
        "выполнение",
        "услуг",
        "работ",
        "для",
        "на",
        "по",
        "в",
        "с",
        "и",
        "или",
        "из",
        "к",
        "за",
        "закупка",
        "закупки",
        "году",
        "год",
    ]
)


def words(text):
    return set(re.findall(r"[\w-]{3,}", text.lower())) - STOP


def feature_row(query, card, supplier, category, customer, retrieval, cutoff, card_count):
    tokens = words(query["query_text"])
    overlap = len(tokens & words(card["profile_text"])) / max(len(tokens), 1)
    values = [*retrieval, overlap]
    for history in (supplier, category, customer):
        count = float(history.get("participations", 0))
        wins = float(history.get("wins", 0))
        values += [count, wins, (wins + 1) / (count + 2)]
    latest = card.get("profile_last_date")
    if isinstance(latest, str):
        latest = date.fromisoformat(latest[:10])
    age = (cutoff - latest).days if latest else 3650
    price = query.get("start_price")
    mean = supplier.get("mean_log_price")
    distance = (
        abs(math.log1p(price) - mean)
        if price is not None and price >= 0 and mean is not None
        else float("nan")
    )
    values += [
        float(card.get("example_count", 0)),
        max(age, 0),
        distance,
        float(not query.get("customer_inn")),
        float(price is None),
        card_count,
    ]
    if len(values) != len(FEATURES):
        raise ValueError("Feature schema mismatch")
    return [float(value) for value in values]
