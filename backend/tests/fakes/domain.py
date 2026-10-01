from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid5

from src.models.candidate import Highlight, ProductMatch, SupplierCandidate
from src.models.enums import (
    Availability,
    CandidateStatus,
    CheckReason,
    CompanyRole,
    EvidenceKind,
    HighlightCode,
    ItemType,
    MatchBasis,
    MatchStatus,
    SourceType,
    SupplierRole,
    VerificationStatus,
)
from src.models.evidence import Evidence
from src.models.offer import Offer
from src.models.offer_evidence import OfferEvidence
from src.models.purchase import PurchaseSummary
from src.models.query_item import Quantity, QueryItem, SearchRequest
from src.models.scoring import ChannelRank, Score, ScoreBreakdown
from src.models.search import CandidateLimit, SearchQuery, SearchText
from src.models.search_result import PipelineInfo, SearchResult
from src.models.source import Source
from src.models.supplier import Supplier

MOMENT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
CHECKED = datetime(2026, 9, 29, 8, 0, tzinfo=UTC)
NAMESPACE = UUID("8f1d7c2e-0000-4000-8000-000000000000")


def uid(name: str) -> UUID:
    return uuid5(NAMESPACE, name)


def make_query(text: str = "крупа гречневая 500 кг; рис", limit: int = 20) -> SearchQuery:
    return SearchQuery(text=SearchText(text), limit=CandidateLimit(limit))


def make_item(item_id: str = "i1", name: str = "Крупа гречневая") -> QueryItem:
    return QueryItem(
        item_id=item_id,
        name=name,
        item_type=ItemType.GOODS,
        quantity=Quantity(Decimal(500), "кг"),
    )


def make_request(*items: QueryItem, query: SearchQuery | None = None) -> SearchRequest:
    return SearchRequest(query=query or make_query(), items=items or (make_item(),))


def make_supplier(name: str = "alpha", inn: str | None = "7801234567") -> Supplier:
    return Supplier(
        supplier_id=uid(name),
        name=f"ООО «{name}»",
        inn=inn,
        region="78",
        website=f"https://{name}.example.org",
        contacts={"email": f"sales@{name}.example.org", "phone": "+7 812 000-00-00"},
        identity_status=VerificationStatus.VERIFIED,
    )


def make_source(
    name: str = "catalog",
    source_type: SourceType = SourceType.DIRECTORY,
    supplier_id: UUID | None = None,
) -> Source:
    return Source(
        source_id=uid(f"source:{name}"),
        name=f"Источник {name}",
        base_url=f"https://{name}.example.org",
        source_type=source_type,
        provider_name=name,
        supplier_id=supplier_id,
    )


def make_offer(
    name: str = "offer",
    supplier: Supplier | None = None,
    role: SupplierRole = SupplierRole.DISTRIBUTOR,
    availability: Availability = Availability.AVAILABLE,
    seller_status: VerificationStatus = VerificationStatus.VERIFIED,
    price: Decimal | None = Decimal("84.50"),
) -> Offer:
    owner = supplier or make_supplier()
    return Offer(
        offer_id=uid(f"offer:{name}"),
        source_id=make_source().source_id,
        external_id=name,
        url=f"https://catalog.example.org/products/{name}",
        name=f"Товар {name}",
        first_seen_at=CHECKED,
        last_seen_at=CHECKED,
        supplier_id=owner.supplier_id,
        seller_status=seller_status,
        item_type=ItemType.GOODS,
        price=price,
        currency="RUB",
        unit="кг",
        availability=availability,
        supplier_role=role,
        role_evidence_url=f"https://catalog.example.org/companies/{owner.supplier_id}",
        role_evidence_text="Дистрибьютор",
    )


def make_offer_evidence(
    offer: Offer | None = None,
    source: Source | None = None,
    match_status: MatchStatus = MatchStatus.ACCEPTED,
) -> OfferEvidence:
    return OfferEvidence(
        offer=offer or make_offer(),
        source=source or make_source(),
        match_status=match_status,
    )


def make_evidence(kind: EvidenceKind = EvidenceKind.PRICE) -> Evidence:
    return Evidence(
        kind=kind,
        title="Прайс-лист",
        url="https://alpha.example.org/price",
        checked_at=CHECKED,
    )


def make_score(total: float = 0.8, channel: str = "lexical", rank: int = 1) -> ScoreBreakdown:
    return ScoreBreakdown(
        fusion=Score(0.9),
        coverage=Score(1.0),
        evidence=Score(0.8),
        history=Score(0.4),
        total=Score(total),
        channels=(ChannelRank(channel, rank),),
    )


def make_candidate(
    supplier: Supplier | None = None,
    rank: int = 1,
    reasons: tuple[CheckReason, ...] = (),
    item_id: str = "i1",
) -> SupplierCandidate:
    owner = supplier or make_supplier()
    offer = make_offer(supplier=owner)
    return SupplierCandidate(
        supplier=owner,
        role=CompanyRole.DISTRIBUTOR,
        status=CandidateStatus.CHECK if reasons else CandidateStatus.RECOMMENDED,
        score=make_score(),
        rank=rank,
        role_evidence=make_evidence(EvidenceKind.CATALOG),
        check_reasons=reasons,
        matches=(
            ProductMatch(
                item_id=item_id,
                basis=MatchBasis.STOCK,
                offer_id=offer.offer_id,
                evidence=make_evidence(),
            ),
        ),
        history=PurchaseSummary(similar=3, wins=1),
        highlights=(Highlight(HighlightCode.COVERS_ITEMS, {"matched": 1, "total": 1}),),
    )


def make_result(*candidates: SupplierCandidate, items: tuple[QueryItem, ...] = ()) -> SearchResult:
    return SearchResult(
        search_id=uid("search"),
        query=make_query(),
        items=items or (make_item(),),
        candidates=candidates,
        pipeline=PipelineInfo(version="search-v1", channels=("lexical",), as_of=MOMENT),
        created_at=MOMENT,
    )
