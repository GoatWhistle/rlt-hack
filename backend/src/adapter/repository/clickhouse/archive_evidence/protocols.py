from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from src.models.purchase import PurchaseSummary
from src.models.query_item import QueryItem


class TextAnalyzer(Protocol):
    def analyze(self, text: str) -> tuple[str, ...]: ...

    def prefixes(self, text: str) -> tuple[str, ...]: ...


class PurchaseHistory(Protocol):
    async def summarize(
        self, supplier_ids: Sequence[UUID], items: Sequence[QueryItem], records: int
    ) -> Mapping[UUID, PurchaseSummary]: ...
