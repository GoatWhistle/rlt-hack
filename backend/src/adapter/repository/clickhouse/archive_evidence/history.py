import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from src.adapter.repository.clickhouse.archive_evidence.protocols import TextAnalyzer
from src.adapter.repository.clickhouse.archive_evidence.query import evidence_statement
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.retrieval.terms import needles_for
from src.adapter.repository.clickhouse.rows import to_uuid
from src.models.enums import PurchaseOutcome
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.query_item import QueryItem

MATCH_SHARE = 0.5
MAX_NEEDLES = 255


@dataclass(frozen=True, slots=True)
class ArchiveLot:
    supplier_id: UUID
    category: str
    lot_id: str
    title: str
    won: bool
    category_lots: int
    category_wins: int
    text: str


@dataclass(frozen=True, slots=True)
class MatchedLot:
    lot: ArchiveLot
    item_ids: tuple[str, ...]


def _summary(lots: Sequence[MatchedLot], records: int) -> PurchaseSummary:
    by_category: dict[str, list[MatchedLot]] = {}
    for entry in lots:
        by_category.setdefault(entry.lot.category, []).append(entry)
    chosen = max(
        by_category.values(),
        key=lambda group: (group[0].lot.category_lots, len(group), group[0].lot.category),
    )
    head = chosen[0].lot
    similar = max(head.category_lots, len(chosen))
    ordered = sorted(chosen, key=lambda entry: (not entry.lot.won, -len(entry.item_ids)))
    kept = ordered[: max(records, 0)]
    return PurchaseSummary(
        similar=similar,
        wins=min(max(head.category_wins, sum(entry.lot.won for entry in chosen)), similar),
        records=tuple(
            PurchaseRecord(
                entry.lot.lot_id,
                entry.lot.title or entry.lot.lot_id,
                PurchaseOutcome.WINNER if entry.lot.won else PurchaseOutcome.PARTICIPANT,
                entry.item_ids,
            )
            for entry in kept
        ),
    )


class ClickHouseArchiveEvidence:
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
            evidence_statement(self._db),
            {
                "ids": [str(value) for value in dict.fromkeys(supplier_ids)],
                "needles": list(needles[:MAX_NEEDLES]),
                "cap": self._cap,
            },
        )
        lots = [_lot(row) for row in rows]
        return await asyncio.to_thread(self._summaries, lots, items, records)

    def _summaries(
        self, lots: Sequence[ArchiveLot], items: Sequence[QueryItem], records: int
    ) -> dict[UUID, PurchaseSummary]:
        wanted = {item.item_id: frozenset(self._analyzer.analyze(item.name)) for item in items}
        grouped: dict[UUID, list[MatchedLot]] = {}
        for lot in lots:
            stems = frozenset(self._analyzer.analyze(lot.text))
            matched = tuple(
                item_id
                for item_id, terms in wanted.items()
                if terms and len(terms & stems) / len(terms) >= MATCH_SHARE
            )
            if matched:
                grouped.setdefault(lot.supplier_id, []).append(MatchedLot(lot, matched))
        return {supplier: _summary(found, records) for supplier, found in grouped.items()}


def _lot(row: Sequence[object]) -> ArchiveLot:
    title, products = str(row[3] or ""), str(row[7] or "")
    return ArchiveLot(
        supplier_id=to_uuid(row[0]),
        category=str(row[1]),
        lot_id=str(row[2]),
        title=title,
        won=bool(int(str(row[4]))),
        category_lots=int(str(row[5])),
        category_wins=int(str(row[6])),
        text=f"{title} {products}",
    )
