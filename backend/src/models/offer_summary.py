import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Self
from uuid import UUID

from src.models.enums import Availability, VerificationStatus
from src.models.evidence import Evidence
from src.models.offer_evidence import OfferEvidence

ATTRIBUTE_LIMIT = 3
SERVICE_KEY = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True, slots=True)
class OfferAttribute:
    name: str
    value: str


def notable_attributes(raw: Mapping[str, str]) -> tuple[OfferAttribute, ...]:
    found: list[OfferAttribute] = []
    for key, value in raw.items():
        name = " ".join(key.split())
        text = " ".join(value.split())
        if not name or not text or SERVICE_KEY.fullmatch(name):
            continue
        found.append(OfferAttribute(name, text))
        if len(found) == ATTRIBUTE_LIMIT:
            break
    return tuple(found)


@dataclass(frozen=True, slots=True)
class OfferSummary:
    offer_id: UUID
    name: str
    availability: Availability = Availability.UNKNOWN
    seller_status: VerificationStatus = VerificationStatus.UNVERIFIED
    price: Decimal | None = None
    currency: str = ""
    unit: str = ""
    brand: str = ""
    article: str = ""
    okpd2_code: str = ""
    attributes: tuple[OfferAttribute, ...] = ()
    evidence: Evidence | None = None

    @classmethod
    def of(cls, card: OfferEvidence) -> Self:
        offer = card.offer
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
            attributes=notable_attributes(offer.attributes),
            evidence=card.evidence,
        )
