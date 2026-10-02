import re
from dataclasses import replace

from src.models.supplier_search import SupplierCandidate, SupplierPurchase

STOP_WORDS = frozenset({"поставка", "закупка", "для", "нужд", "оказание", "выполнение", "году"})


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zа-я0-9]+", text.casefold().replace("ё", "е"))) - STOP_WORDS


def _priority(query: set[str], purchase: SupplierPurchase) -> tuple[float, str, str]:
    words = _tokens(" ".join((purchase.title, *purchase.product_names)))
    overlap = len(query & words) / max(1, len(query))
    return overlap, purchase.publish_date, purchase.lot_id


async def relevant_evidence(
    text: str, candidates: list[SupplierCandidate]
) -> list[SupplierCandidate]:
    query = _tokens(text)
    return [
        replace(
            candidate,
            purchases=sorted(
                candidate.purchases, key=lambda item: _priority(query, item), reverse=True
            ),
        )
        for candidate in candidates
    ]
