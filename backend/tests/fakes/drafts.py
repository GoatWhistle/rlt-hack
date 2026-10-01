from src.models.candidate import ProductMatch
from src.models.enums import CompanyRole, MatchBasis
from src.models.offer_evidence import OfferEvidence
from src.models.purchase import PurchaseSummary
from src.models.scoring import ChannelRank, Score
from src.models.supplier import Supplier
from src.service.supplier_search.assembly.draft import CandidateDraft
from tests.fakes.domain import make_evidence, make_offer, make_offer_evidence, make_supplier


def stock_match(item_id: str = "i1", card: OfferEvidence | None = None) -> ProductMatch:
    offer = (card or make_offer_evidence()).offer
    return ProductMatch(item_id, MatchBasis.STOCK, offer.offer_id, make_evidence())


def make_draft(
    supplier: Supplier | None = None,
    matches: tuple[ProductMatch, ...] | None = None,
    cards: tuple[OfferEvidence, ...] | None = None,
    role: CompanyRole = CompanyRole.DISTRIBUTOR,
    total_items: int = 1,
    fusion: float = 1.0,
    history: PurchaseSummary | None = None,
    failed: bool = False,
) -> CandidateDraft:
    owner = supplier or make_supplier()
    owned = cards if cards is not None else (make_offer_evidence(make_offer(supplier=owner)),)
    return CandidateDraft(
        supplier=owner,
        role=role,
        role_evidence=make_evidence() if role != CompanyRole.UNKNOWN else None,
        fusion=Score(fusion),
        channels=(ChannelRank("lexical", 1),),
        total_items=total_items,
        matches=matches if matches is not None else (stock_match(),),
        used_offers=owned,
        current_offers=owned,
        history=history or PurchaseSummary.empty(),
        enrichment_failed=failed,
    )
