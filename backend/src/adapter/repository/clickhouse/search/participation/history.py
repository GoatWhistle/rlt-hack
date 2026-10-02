from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from src.adapter.repository.clickhouse.engine.rows import to_uuid
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.search.participation.protocols import TextAnalyzer
from src.adapter.repository.clickhouse.search.participation.query import participations_query
from src.adapter.repository.clickhouse.search.retrieval.similarity import LotSimilarity
from src.adapter.repository.clickhouse.search.retrieval.terms import flags_of, index_terms
from src.models.company.purchase import PurchaseRecord, PurchaseSummary
from src.models.enums import PurchaseOutcome
from src.models.search.query_item import QueryItem

MAX_TERMS = 128


@dataclass(frozen=True, slots=True)
class LotParticipation:
    supplier_id: UUID
    lot_id: str
    won: bool
    title: str
    flags: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class MatchedLot:
    participation: LotParticipation
    item_ids: tuple[str, ...]


def _record(lot: MatchedLot) -> PurchaseRecord:
    outcome = PurchaseOutcome.WINNER if lot.participation.won else PurchaseOutcome.PARTICIPANT
    entry = lot.participation
    return PurchaseRecord(entry.lot_id, entry.title or entry.lot_id, outcome, lot.item_ids)


def _summary(lots: Sequence[MatchedLot], records: int) -> PurchaseSummary:
    ordered = sorted(
        lots,
        key=lambda lot: (not lot.participation.won, -len(lot.item_ids), lot.participation.lot_id),
    )
    return PurchaseSummary(
        similar=len(lots),
        wins=sum(1 for lot in lots if lot.participation.won),
        records=tuple(_record(lot) for lot in ordered[: max(records, 0)]),
    )


class ClickHousePurchaseHistory:
    def __init__(
        self,
        gateway: SqlGateway,
        analyzer: TextAnalyzer,
        database: str = "supplier_search",
        row_cap: int = 5000,
        similarity: LotSimilarity | None = None,
    ) -> None:
        self._gateway = gateway
        self._analyzer = analyzer
        self._db = database
        self._cap = row_cap
        self._similarity = similarity or LotSimilarity()

    async def summarize(
        self, supplier_ids: Sequence[UUID], items: Sequence[QueryItem], records: int
    ) -> Mapping[UUID, PurchaseSummary]:
        wanted = {item.item_id: index_terms(self._analyzer, item.name) for item in items}
        terms = tuple(dict.fromkeys(term for found in wanted.values() for term in found))
        terms = terms[:MAX_TERMS]
        if not supplier_ids or not terms:
            return {}
        statement, match = participations_query(self._db, terms)
        ids = [str(value) for value in dict.fromkeys(supplier_ids)]
        rows = await self._gateway.select(
            statement, {**match.parameters, "ids": ids, "cap": self._cap}
        )
        positions = {term: index for index, term in enumerate(terms)}
        columns = {
            item_id: [positions[term] for term in found if term in positions]
            for item_id, found in wanted.items()
        }
        return self._summaries([_participation(row) for row in rows], columns, records)

    def _summaries(
        self,
        participations: Sequence[LotParticipation],
        columns: Mapping[str, Sequence[int]],
        records: int,
    ) -> dict[UUID, PurchaseSummary]:
        grouped: dict[UUID, list[MatchedLot]] = {}
        for entry in participations:
            matched = tuple(
                item_id
                for item_id, indexes in columns.items()
                if self._similarity.similar([entry.flags[index] for index in indexes])
            )
            if matched:
                grouped.setdefault(entry.supplier_id, []).append(MatchedLot(entry, matched))
        return {supplier: _summary(lots, records) for supplier, lots in grouped.items()}


def _participation(row: Sequence[object]) -> LotParticipation:
    return LotParticipation(
        supplier_id=to_uuid(row[0]),
        lot_id=str(row[1]),
        won=bool(row[2]),
        title=str(row[3] or ""),
        flags=flags_of(row[-1]),
    )
