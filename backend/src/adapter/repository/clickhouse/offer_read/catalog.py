from collections.abc import Mapping, Sequence
from uuid import UUID

from src.adapter.repository.clickhouse.offer_read.mapping import (
    EVIDENCE_FIELDS,
    to_offer_evidence,
)
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.offer_evidence import OfferEvidence

SELECT_EVIDENCE = (
    "SELECT {fields} FROM {db}.offers_current AS o "
    "INNER JOIN {db}.sources_current AS s ON s.source_id = o.source_id "
    "LEFT JOIN {db}.offer_matches_current AS m ON m.offer_id = o.offer_id "
)
BY_OFFER = "WHERE o.offer_id IN {ids:Array(UUID)}"
CURRENT_BY_SUPPLIER = (
    "WHERE o.supplier_id IN {ids:Array(UUID)} AND o.availability != 'unavailable' "
    "ORDER BY o.supplier_id, o.last_seen_at DESC, o.offer_id "
    "LIMIT {per_supplier:UInt32} BY o.supplier_id"
)


def _ids(values: Sequence[UUID]) -> list[str]:
    return [str(value) for value in dict.fromkeys(values)]


class ClickHouseOfferCatalog:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database
        self._select = SELECT_EVIDENCE.format(fields=EVIDENCE_FIELDS, db=database)

    async def get_many(self, offer_ids: Sequence[UUID]) -> Mapping[UUID, OfferEvidence]:
        if not offer_ids:
            return {}
        rows = await self._gateway.select(self._select + BY_OFFER, {"ids": _ids(offer_ids)})
        cards = (to_offer_evidence(row) for row in rows)
        return {card.offer.offer_id: card for card in cards}

    async def current_for(
        self, supplier_ids: Sequence[UUID], per_supplier: int
    ) -> Mapping[UUID, tuple[OfferEvidence, ...]]:
        if not supplier_ids or per_supplier < 1:
            return {}
        rows = await self._gateway.select(
            self._select + CURRENT_BY_SUPPLIER,
            {"ids": _ids(supplier_ids), "per_supplier": per_supplier},
        )
        grouped: dict[UUID, list[OfferEvidence]] = {}
        for row in rows:
            card = to_offer_evidence(row)
            if card.offer.supplier_id is not None:
                grouped.setdefault(card.offer.supplier_id, []).append(card)
        return {supplier_id: tuple(cards) for supplier_id, cards in grouped.items()}
