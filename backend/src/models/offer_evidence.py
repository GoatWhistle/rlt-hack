from dataclasses import dataclass

from src.models.enums import (
    Availability,
    EvidenceKind,
    MatchStatus,
    SourceType,
    SupplierRole,
    VerificationStatus,
)
from src.models.evidence import Evidence, is_web_url
from src.models.offer import Offer
from src.models.source import Source

SOURCE_EVIDENCE = {
    SourceType.DIRECTORY: EvidenceKind.CATALOG,
    SourceType.WEBSITE: EvidenceKind.CATALOG,
    SourceType.FEED: EvidenceKind.PRICE,
    SourceType.PRICE_LIST: EvidenceKind.PRICE,
    SourceType.REGISTRY: EvidenceKind.REGISTRY,
    SourceType.DATASET: EvidenceKind.REGISTRY,
}


@dataclass(frozen=True, slots=True)
class OfferEvidence:
    offer: Offer
    source: Source
    match_status: MatchStatus = MatchStatus.UNMATCHED
    matched_content_hash: str = ""

    @property
    def is_current(self) -> bool:
        return self.offer.availability != Availability.UNAVAILABLE

    @property
    def seller_confirmed(self) -> bool:
        return (
            self.offer.supplier_id is not None
            and self.offer.seller_status == VerificationStatus.VERIFIED
        )

    @property
    def in_stock(self) -> bool:
        return self.offer.availability in (Availability.AVAILABLE, Availability.ON_ORDER)

    @property
    def has_conflict(self) -> bool:
        return VerificationStatus.CONFLICT in (
            self.offer.seller_status,
            self.source.ownership_status,
        )

    @property
    def backs_supplier(self) -> bool:
        return self.seller_confirmed and not self.has_conflict

    @property
    def catalog_confirmed(self) -> bool:
        return (
            self.match_status == MatchStatus.ACCEPTED
            and self.matched_content_hash == self.offer.content_hash
        )

    @property
    def evidence(self) -> Evidence | None:
        if not is_web_url(self.offer.url):
            return None
        kind = SOURCE_EVIDENCE[self.source.source_type]
        if self.offer.price is not None:
            kind = EvidenceKind.PRICE
        return Evidence(
            kind=kind,
            title=self.source.name,
            url=self.offer.url,
            checked_at=self.offer.last_seen_at,
        )

    @property
    def role_evidence(self) -> Evidence | None:
        if self.offer.supplier_role is SupplierRole.UNKNOWN or not is_web_url(self.offer.url):
            return None
        return Evidence(
            kind=SOURCE_EVIDENCE[self.source.source_type],
            title=self.offer.role_evidence_text or self.source.name,
            url=self.offer.url,
            checked_at=self.offer.last_seen_at,
        )
