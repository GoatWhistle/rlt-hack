import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from src.adapter.repository.clickhouse.participation.protocols import TextAnalyzer
from src.adapter.repository.clickhouse.participation.query import participations_statement
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.retrieval.terms import needles_for
from src.adapter.repository.clickhouse.rows import to_uuid
from src.models.enums import PurchaseOutcome
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.query_item import QueryItem

MATCH_SHARE = 0.5
MAX_NEEDLES = 255


@dataclass(frozen=True, slots=True)
class LotParticipation:
    supplier_id: UUID
    lot_id: str
    won: bool
    title: str
    text: str


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
    ) -> None:
        self._gateway = gateway
        self._analyzer = analyzer
        self._db = database
        self._cap = row_cap

    async def summarize(
        self, supplier_ids: Sequence[UUID], items: Sequence[QueryItem], records: int
    ) -> Mapping[UUID, PurchaseSummary]:
        needles = tuple(
            dict.fromkeys(
                needle for item in items for needle in needles_for(self._analyzer, item.name)
            )
        )
        if not supplier_ids or not needles:
            return {}
        rows = await self._gateway.select(
            participations_statement(self._db),
            {
                "ids": [str(value) for value in dict.fromkeys(supplier_ids)],
                "needles": list(needles[:MAX_NEEDLES]),
                "cap": self._cap,
            },
        )
        participations = [_participation(row) for row in rows]
        return await asyncio.to_thread(self._summaries, participations, items, records)

    def _summaries(
        self,
        participations: Sequence[LotParticipation],
        items: Sequence[QueryItem],
        records: int,
    ) -> dict[UUID, PurchaseSummary]:
        wanted = {item.item_id: frozenset(self._analyzer.analyze(item.name)) for item in items}
        grouped: dict[UUID, list[MatchedLot]] = {}
        for entry in participations:
            stems = frozenset(self._analyzer.analyze(entry.text))
            matched = tuple(
                item_id
                for item_id, terms in wanted.items()
                if terms and len(terms & stems) / len(terms) >= MATCH_SHARE
            )
            if matched:
                grouped.setdefault(entry.supplier_id, []).append(MatchedLot(entry, matched))
        return {supplier: _summary(lots, records) for supplier, lots in grouped.items()}


def _participation(row: Sequence[object]) -> LotParticipation:
    subject, procedure, products = str(row[3] or ""), str(row[4] or ""), str(row[5] or "")
    return LotParticipation(
        supplier_id=to_uuid(row[0]),
        lot_id=str(row[1]),
        won=bool(int(str(row[2]))),
        title=subject or procedure,
        text=" ".join((subject, procedure, products)),
    )
