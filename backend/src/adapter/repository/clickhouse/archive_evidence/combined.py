import asyncio
from collections.abc import Mapping, Sequence
from uuid import UUID

from src.adapter.repository.clickhouse.archive_evidence.protocols import PurchaseHistory
from src.models.purchase import PurchaseSummary
from src.models.query_item import QueryItem


class CombinedPurchaseHistory:
    def __init__(self, *sources: PurchaseHistory) -> None:
        self._sources = sources

    async def summarize(
        self, supplier_ids: Sequence[UUID], items: Sequence[QueryItem], records: int
    ) -> Mapping[UUID, PurchaseSummary]:
        found = await asyncio.gather(
            *(source.summarize(supplier_ids, items, records) for source in self._sources)
        )
        merged: dict[UUID, PurchaseSummary] = {}
        for summaries in found:
            for supplier, summary in summaries.items():
                current = merged.get(supplier)
                if current is None or summary.similar > current.similar:
                    merged[supplier] = summary
        return merged
