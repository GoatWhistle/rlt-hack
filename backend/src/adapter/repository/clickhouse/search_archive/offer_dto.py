from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from src.adapter.repository.clickhouse.search_archive.query_dto import FrozenDto
from src.models.enums import Availability, LinkMethod, RequirementStatus, SourceType
from src.models.offer_snapshot import OfferSnapshot
from src.models.requirement import Requirement, RequirementCheck


class RequirementDto(FrozenDto):
    key: str
    value: str
    text: str

    @classmethod
    def from_domain(cls, requirement: Requirement) -> Self:
        return cls(key=requirement.key, value=requirement.value, text=requirement.text)

    def to_domain(self) -> Requirement:
        return Requirement(self.key, self.value, self.text)


class CheckDto(FrozenDto):
    requirement: RequirementDto
    status: RequirementStatus
    found: str = ""

    @classmethod
    def from_domain(cls, check: RequirementCheck) -> Self:
        return cls(
            requirement=RequirementDto.from_domain(check.requirement),
            status=check.status,
            found=check.found,
        )

    def to_domain(self) -> RequirementCheck:
        return RequirementCheck(self.requirement.to_domain(), self.status, self.found)


class OfferSnapshotDto(FrozenDto):
    offer_id: UUID
    name: str
    url: str
    source_name: str
    source_type: SourceType
    observed_at: datetime
    link: LinkMethod
    brand: str = ""
    article: str = ""
    unit: str = ""
    price: Decimal | None = None
    currency: str = ""
    availability: Availability = Availability.UNKNOWN

    @classmethod
    def maybe(cls, offer: OfferSnapshot | None) -> Self | None:
        if offer is None:
            return None
        return cls(
            offer_id=offer.offer_id,
            name=offer.name,
            url=offer.url,
            source_name=offer.source_name,
            source_type=offer.source_type,
            observed_at=offer.observed_at,
            link=offer.link,
            brand=offer.brand,
            article=offer.article,
            unit=offer.unit,
            price=offer.price,
            currency=offer.currency,
            availability=offer.availability,
        )

    def to_domain(self) -> OfferSnapshot:
        return OfferSnapshot(
            offer_id=self.offer_id,
            name=self.name,
            url=self.url,
            source_name=self.source_name,
            source_type=self.source_type,
            observed_at=self.observed_at,
            link=self.link,
            brand=self.brand,
            article=self.article,
            unit=self.unit,
            price=self.price,
            currency=self.currency,
            availability=self.availability,
        )
