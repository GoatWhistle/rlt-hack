from collections.abc import Mapping, Sequence
from uuid import UUID

from src.adapter.repository.clickhouse.offer_read.mapping import (
    EVIDENCE_FIELDS,
    to_offer_evidence,
)
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.rows import to_uuid
from src.models.offer_evidence import OfferEvidence

SELECT_EVIDENCE = (
    "SELECT {fields} FROM {db}.offers_current AS o "
    "INNER JOIN {db}.sources_current AS s ON s.source_id = o.source_id "
    "LEFT JOIN {db}.offer_matches_current AS m ON m.offer_id = o.offer_id "
)
BY_OFFER = "WHERE o.offer_id IN {ids:Array(UUID)}"
CURRENT_IDS = (
    "SELECT o.supplier_id, o.offer_id FROM {db}.offers_current AS o "
    "WHERE o.supplier_id IN {{ids:Array(UUID)}} AND o.availability != 'unavailable' "
    "ORDER BY o.supplier_id, o.last_seen_at DESC, o.offer_id "
    "LIMIT {{per_supplier:UInt32}} BY o.supplier_id"
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

    async def current_ids(
        self, supplier_ids: Sequence[UUID], per_supplier: int
    ) -> Mapping[UUID, tuple[UUID, ...]]:
        if not supplier_ids or per_supplier < 1:
            return {}
        rows = await self._gateway.select(
            CURRENT_IDS.format(db=self._db),
            {"ids": _ids(supplier_ids), "per_supplier": per_supplier},
        )
        grouped: dict[UUID, list[UUID]] = {}
        for supplier_id, offer_id in rows:
            grouped.setdefault(to_uuid(supplier_id), []).append(to_uuid(offer_id))
        return {supplier_id: tuple(offers) for supplier_id, offers in grouped.items()}

    async def current_for(
        self, supplier_ids: Sequence[UUID], per_supplier: int
    ) -> Mapping[UUID, tuple[OfferEvidence, ...]]:
        ids = await self.current_ids(supplier_ids, per_supplier)
        cards = await self.get_many([offer for owned in ids.values() for offer in owned])
        found = {
            supplier_id: tuple(cards[offer] for offer in owned if offer in cards)
            for supplier_id, owned in ids.items()
        }
        return {supplier_id: owned for supplier_id, owned in found.items() if owned}
