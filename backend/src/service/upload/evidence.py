import re
from dataclasses import replace

from src.models.operations.upload import NoticePosition
from src.models.search.supplier_search import SupplierCandidate, SupplierPurchase
from src.service.upload.protocols import PositionTokenizer

STOP_WORDS = frozenset({"поставка", "закупка", "для", "нужд", "оказание", "выполнение", "году"})


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zа-я0-9]+", text.casefold().replace("ё", "е"))) - STOP_WORDS


def _position_tokens(text: str) -> tuple[str, ...]:
    return tuple(sorted(_tokens(text)))


def _priority(query: set[str], purchase: SupplierPurchase) -> tuple[float, str, str]:
    words = _tokens(" ".join((purchase.title, *purchase.product_names)))
    overlap = len(query & words) / max(1, len(query))
    return overlap, purchase.publish_date, purchase.lot_id


async def relevant_evidence(
    text: str,
    candidates: list[SupplierCandidate],
    positions: tuple[NoticePosition, ...] = (),
    position_tokens: PositionTokenizer | None = None,
) -> list[SupplierCandidate]:
    query = _tokens(text)
    tokenize = position_tokens or _position_tokens
    result = []
    for candidate in candidates:
        purchases = sorted(
            candidate.purchases, key=lambda item: _priority(query, item), reverse=True
        )
        evidence = {}
        for position in positions:
            required = set(tokenize(position.name))
            if not required:
                continue
            for purchase in purchases:
                if any(required <= set(tokenize(name)) for name in purchase.product_names):
                    evidence[position.item_id] = purchase.lot_id
                    break
        result.append(replace(candidate, purchases=purchases, position_evidence=evidence))
    return result
