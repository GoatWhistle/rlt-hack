from decimal import Decimal
from typing import Self
from uuid import UUID

from src.adapter.repository.clickhouse.search_archive.candidate_dto import EvidenceDto
from src.adapter.repository.clickhouse.search_archive.query_dto import FrozenDto
from src.models.enums import Availability, VerificationStatus
from src.models.offer_summary import OfferAttribute, OfferSummary


class OfferSummaryDto(FrozenDto):
    offer_id: UUID
    name: str
    availability: Availability
    seller_status: VerificationStatus
    price: Decimal | None
    currency: str
    unit: str
    brand: str
    article: str
    okpd2_code: str
    attributes: tuple[tuple[str, str], ...]
    evidence: EvidenceDto | None

    @classmethod
    def from_domain(cls, offer: OfferSummary) -> Self:
        return cls(
            offer_id=offer.offer_id,
            name=offer.name,
            availability=offer.availability,
            seller_status=offer.seller_status,
            price=offer.price,
            currency=offer.currency,
            unit=offer.unit,
            brand=offer.brand,
            article=offer.article,
            okpd2_code=offer.okpd2_code,
            attributes=tuple((item.name, item.value) for item in offer.attributes),
            evidence=EvidenceDto.maybe(offer.evidence),
        )

    def to_domain(self) -> OfferSummary:
        return OfferSummary(
            offer_id=self.offer_id,
            name=self.name,
            availability=self.availability,
            seller_status=self.seller_status,
            price=self.price,
            currency=self.currency,
            unit=self.unit,
            brand=self.brand,
            article=self.article,
            okpd2_code=self.okpd2_code,
            attributes=tuple(OfferAttribute(name, value) for name, value in self.attributes),
            evidence=None if self.evidence is None else self.evidence.to_domain(),
        )
