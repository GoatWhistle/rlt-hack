from datetime import datetime
from typing import Self
from uuid import UUID

from src.adapter.repository.clickhouse.search_archive.query_dto import FrozenDto
from src.models.candidate import Highlight, ProductMatch
from src.models.enums import (
    EvidenceKind,
    HighlightCode,
    MatchBasis,
    PurchaseOutcome,
    VerificationStatus,
)
from src.models.evidence import Evidence
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.scoring import ChannelRank, Score, ScoreBreakdown
from src.models.supplier import Supplier


class SupplierDto(FrozenDto):
    supplier_id: UUID
    name: str
    inn: str | None
    kpps: tuple[str, ...]
    legal_status: str
    region: str
    website: str
    contacts: dict[str, str]
    okved_codes: tuple[str, ...]
    identity_status: VerificationStatus
    identity_evidence_url: str

    @classmethod
    def from_domain(cls, supplier: Supplier) -> Self:
        return cls(
            supplier_id=supplier.supplier_id,
            name=supplier.name,
            inn=supplier.inn,
            kpps=supplier.kpps,
            legal_status=supplier.legal_status,
            region=supplier.region,
            website=supplier.website,
            contacts=dict(supplier.contacts),
            okved_codes=supplier.okved_codes,
            identity_status=supplier.identity_status,
            identity_evidence_url=supplier.identity_evidence_url,
        )

    def to_domain(self) -> Supplier:
        return Supplier(
            supplier_id=self.supplier_id,
            name=self.name,
            inn=self.inn,
            kpps=self.kpps,
            legal_status=self.legal_status,
            region=self.region,
            website=self.website,
            contacts=dict(self.contacts),
            okved_codes=self.okved_codes,
            identity_status=self.identity_status,
            identity_evidence_url=self.identity_evidence_url,
        )


class EvidenceDto(FrozenDto):
    kind: EvidenceKind
    title: str
    url: str
    checked_at: datetime

    @classmethod
    def from_domain(cls, evidence: Evidence) -> Self:
        return cls(
            kind=evidence.kind,
            title=evidence.title,
            url=evidence.url,
            checked_at=evidence.checked_at,
        )

    @classmethod
    def maybe(cls, evidence: Evidence | None) -> Self | None:
        return None if evidence is None else cls.from_domain(evidence)

    def to_domain(self) -> Evidence:
        return Evidence(self.kind, self.title, self.url, self.checked_at)


class MatchDto(FrozenDto):
    item_id: str
    basis: MatchBasis
    offer_id: UUID | None
    evidence: EvidenceDto | None

    @classmethod
    def from_domain(cls, match: ProductMatch) -> Self:
        evidence = EvidenceDto.maybe(match.evidence)
        return cls(
            item_id=match.item_id, basis=match.basis, offer_id=match.offer_id, evidence=evidence
        )

    def to_domain(self) -> ProductMatch:
        evidence = None if self.evidence is None else self.evidence.to_domain()
        return ProductMatch(self.item_id, self.basis, self.offer_id, evidence)


class RecordDto(FrozenDto):
    lot_id: str
    title: str
    outcome: PurchaseOutcome
    item_ids: tuple[str, ...]


class HistoryDto(FrozenDto):
    similar: int
    wins: int
    records: tuple[RecordDto, ...]

    @classmethod
    def from_domain(cls, history: PurchaseSummary) -> Self:
        records = tuple(
            RecordDto(
                lot_id=item.lot_id, title=item.title, outcome=item.outcome, item_ids=item.item_ids
            )
            for item in history.records
        )
        return cls(similar=history.similar, wins=history.wins, records=records)

    def to_domain(self) -> PurchaseSummary:
        records = tuple(
            PurchaseRecord(item.lot_id, item.title, item.outcome, item.item_ids)
            for item in self.records
        )
        return PurchaseSummary(self.similar, self.wins, records)


class HighlightDto(FrozenDto):
    code: HighlightCode
    params: dict[str, int]

    @classmethod
    def from_domain(cls, highlight: Highlight) -> Self:
        return cls(code=highlight.code, params=dict(highlight.params))

    def to_domain(self) -> Highlight:
        return Highlight(self.code, self.params)


class ScoreDto(FrozenDto):
    fusion: float
    coverage: float
    evidence: float
    history: float
    total: float
    channels: tuple[tuple[str, int], ...]

    @classmethod
    def from_domain(cls, score: ScoreBreakdown) -> Self:
        return cls(
            fusion=score.fusion.value,
            coverage=score.coverage.value,
            evidence=score.evidence.value,
            history=score.history.value,
            total=score.total.value,
            channels=tuple((item.channel, item.rank) for item in score.channels),
        )

    def to_domain(self) -> ScoreBreakdown:
        return ScoreBreakdown(
            fusion=Score(self.fusion),
            coverage=Score(self.coverage),
            evidence=Score(self.evidence),
            history=Score(self.history),
            total=Score(self.total),
            channels=tuple(ChannelRank(channel, rank) for channel, rank in self.channels),
        )
