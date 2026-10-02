from collections.abc import Sequence

from src.models.candidate import ProductMatch
from src.models.company_role import assess_role
from src.models.offer_evidence import OfferEvidence
from src.models.query_item import QueryItem
from src.models.supplier import Supplier
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.assembly.highlights import HighlightComposer
from src.service.supplier_search.assembly.match import MatchResolver
from src.service.supplier_search.enrichment.bundle import Enrichment
from src.service.supplier_search.fusion.candidate import FusedCandidate, ItemRefs


class CandidateAssembler:
    def __init__(self, matches: MatchResolver, highlights: HighlightComposer) -> None:
        self._matches = matches
        self._highlights = highlights

    def assemble(
        self,
        fused: FusedCandidate,
        items: Sequence[QueryItem],
        enrichment: Enrichment,
    ) -> CandidateDraft | None:
        supplier = enrichment.suppliers.get(fused.supplier_id)
        if supplier is None or not items:
            return None
        used = self._used_cards(fused, supplier, enrichment)
        history = enrichment.history_of(supplier.supplier_id)
        current = enrichment.current_of(supplier.supplier_id)
        matches = self._resolve_matches(fused, items, used, history.item_ids)
        role = assess_role((*current, *used))
        return CandidateDraft(
            supplier=supplier,
            role=role.role,
            role_evidence=role.evidence,
            fusion=fused.fusion,
            channels=fused.channels,
            total_items=len(items),
            matches=matches,
            used_offers=used,
            current_offers=current,
            history=history,
            highlights=self._highlights.compose(supplier, matches, used, history, len(items)),
            enrichment_failed=enrichment.degraded,
        )

    def _used_cards(
        self, fused: FusedCandidate, supplier: Supplier, enrichment: Enrichment
    ) -> tuple[OfferEvidence, ...]:
        cards = (enrichment.offers.get(offer_id) for offer_id in fused.offer_ids)
        return tuple(
            card
            for card in cards
            if card is not None and card.offer.supplier_id == supplier.supplier_id
        )

    def _resolve_matches(
        self,
        fused: FusedCandidate,
        items: Sequence[QueryItem],
        used: Sequence[OfferEvidence],
        historic: frozenset[str],
    ) -> tuple[ProductMatch, ...]:
        by_id = {card.offer.offer_id: card for card in used}
        resolved: list[ProductMatch] = []
        for item in items:
            refs = fused.items.get(item.item_id, ItemRefs())
            cards = [by_id[offer_id] for offer_id in refs.offer_ids if offer_id in by_id]
            signalled = item.item_id in fused.items or item.item_id in historic
            match = self._matches.resolve(item.item_id, cards, signalled, refs.inferred_offer_ids)
            if match is not None:
                resolved.append(match)
        return tuple(resolved)
