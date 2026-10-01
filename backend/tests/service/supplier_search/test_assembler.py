from src.models.enums import CompanyRole, MatchBasis, PurchaseOutcome
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.scoring import ChannelRank, Score
from src.service.supplier_search.assembly.assembler import CandidateAssembler
from src.service.supplier_search.assembly.highlights import HighlightComposer
from src.service.supplier_search.assembly.match import MatchResolver
from src.service.supplier_search.assembly.role import RoleResolver
from src.service.supplier_search.enrichment.bundle import Enrichment
from src.service.supplier_search.fusion.candidate import FusedCandidate, ItemRefs
from tests.fakes.domain import make_item, make_offer, make_offer_evidence, make_supplier

ALPHA = make_supplier("alpha")
BETA = make_supplier("beta")
ITEMS = (make_item("i1"), make_item("i2", "Рис"), make_item("i3", "Соль"))


def assembler() -> CandidateAssembler:
    return CandidateAssembler(RoleResolver(), MatchResolver(), HighlightComposer())


def test_draft_uses_only_cards_of_the_candidate_and_history_items() -> None:
    own = make_offer_evidence(make_offer("own", supplier=ALPHA))
    foreign = make_offer_evidence(make_offer("foreign", supplier=BETA))
    fused = FusedCandidate(
        ALPHA.supplier_id,
        Score(0.7),
        (ChannelRank("lexical", 1),),
        {"i1": ItemRefs((foreign.offer.offer_id, own.offer.offer_id)), "i9": ItemRefs()},
    )
    record = PurchaseRecord("lot-1", "Поставка риса", PurchaseOutcome.WINNER, ("i2",))
    enrichment = Enrichment(
        suppliers={ALPHA.supplier_id: ALPHA},
        offers={card.offer.offer_id: card for card in (own, foreign)},
        histories={ALPHA.supplier_id: PurchaseSummary(1, 1, (record,))},
    )
    draft = assembler().assemble(fused, ITEMS, enrichment)
    assert draft is not None
    assert draft.used_offers == (own,)
    assert draft.current_offers == ()
    assert [(match.item_id, match.basis) for match in draft.matches] == [
        ("i1", MatchBasis.STOCK),
        ("i2", MatchBasis.INFERRED),
    ]
    assert (draft.role, draft.role_evidence) == (CompanyRole.DISTRIBUTOR, own.role_evidence)
    assert draft.total_items == 3
    assert draft.fusion == Score(0.7)
    assert not draft.enrichment_failed


def test_candidate_without_directory_record_is_dropped() -> None:
    fused = FusedCandidate(ALPHA.supplier_id, Score(0.5))
    assert assembler().assemble(fused, ITEMS, Enrichment()) is None
    known = Enrichment(suppliers={ALPHA.supplier_id: ALPHA}, failed=frozenset({"offers"}))
    assert assembler().assemble(fused, (), known) is None
    draft = assembler().assemble(fused, ITEMS, known)
    assert draft is not None
    assert draft.enrichment_failed
    assert draft.matches == ()
