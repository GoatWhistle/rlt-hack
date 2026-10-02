from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from src.models.enums import Availability, LinkMethod, SourceType
from src.models.offer_evidence import OfferEvidence


@dataclass(frozen=True, slots=True)
class OfferSnapshot:
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
    def of(cls, card: OfferEvidence) -> Self:
        offer = card.offer
        if card.catalog_confirmed and card.backs_supplier:
            link = LinkMethod.CATALOG_ACCEPTED
        elif card.backs_supplier:
            link = LinkMethod.SELLER_VERIFIED
        else:
            link = LinkMethod.UNVERIFIED
        return cls(
            offer_id=offer.offer_id,
            name=offer.name,
            url=offer.url,
            source_name=card.source.name,
            source_type=card.source.source_type,
            observed_at=offer.last_seen_at,
            link=link,
            brand=offer.brand,
            article=offer.article,
            unit=offer.unit,
            price=offer.price,
            currency=offer.currency,
            availability=offer.availability,
        )
