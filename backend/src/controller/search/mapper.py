import re
from uuid import UUID

from src.controller.http.schema import plain_decimal, score
from src.controller.search.dto import (
    CandidateDto,
    ChannelRankDto,
    ContactsDto,
    HighlightDto,
    HistoryDto,
    ItemDto,
    MatchDto,
    PipelineDto,
    PurchaseDto,
    QuantityDto,
    ScoreDto,
    SearchResponseDto,
    SearchSummaryDto,
    SourceDto,
    WarningDto,
)
from src.controller.search.query_mapper import query_dto
from src.models.candidate import Highlight, ProductMatch, SupplierCandidate
from src.models.evidence import Evidence, is_web_url
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.query_item import QueryItem
from src.models.scoring import ScoreBreakdown
from src.models.search_result import PipelineInfo, SearchResult, SearchSummary, SearchWarning
from src.models.supplier import Supplier
from src.service.errors import SearchNotFoundError

EMAIL = re.compile(r"[^@\s?&#/:]+@[^@\s?&#/:]+\.[^@\s?&#/:]+")


def parse_search_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as error:
        raise SearchNotFoundError from error


def source_dto(evidence: Evidence | None) -> SourceDto | None:
    if evidence is None:
        return None
    return SourceDto(
        kind=evidence.kind,
        title=evidence.title,
        url=evidence.url,
        checked_at=evidence.checked_at,
    )


def web_site(raw: str) -> str:
    return raw.strip() if is_web_url(raw) else ""


def email_address(raw: str) -> str:
    value = raw.strip()
    return value if EMAIL.fullmatch(value) else ""


def contacts_dto(supplier: Supplier) -> ContactsDto:
    return ContactsDto(
        site=web_site(supplier.website),
        email=email_address(supplier.contacts.get("email") or ""),
        phone=supplier.contacts.get("phone") or "",
    )


def item_dto(item: QueryItem) -> ItemDto:
    quantity = item.quantity
    return ItemDto(
        id=item.item_id,
        name=item.name,
        okpd2=item.okpd2,
        item_type=item.item_type,
        origin=item.origin,
        quantity=None
        if quantity is None
        else QuantityDto(value=plain_decimal(quantity.value), unit=quantity.unit),
    )


def match_dto(match: ProductMatch) -> MatchDto:
    return MatchDto(
        item_id=match.item_id,
        basis=match.basis,
        offer_id=match.offer_id,
        source=source_dto(match.evidence),
    )


def purchase_dto(record: PurchaseRecord) -> PurchaseDto:
    return PurchaseDto(
        lot_id=record.lot_id,
        title=record.title,
        outcome=record.outcome,
        item_ids=list(record.item_ids),
    )


def history_dto(history: PurchaseSummary) -> HistoryDto:
    return HistoryDto(
        similar_purchases=history.similar,
        wins=history.wins,
        records=[purchase_dto(record) for record in history.records],
    )


def highlight_dto(highlight: Highlight) -> HighlightDto:
    return HighlightDto(code=highlight.code, params=dict(highlight.params))


def score_dto(breakdown: ScoreBreakdown) -> ScoreDto:
    return ScoreDto(
        total=score(breakdown.total.value),
        fusion=score(breakdown.fusion.value),
        coverage=score(breakdown.coverage.value),
        evidence=score(breakdown.evidence.value),
        history=score(breakdown.history.value),
        channels=[
            ChannelRankDto(channel=channel.channel, rank=channel.rank)
            for channel in breakdown.channels
        ],
    )


def candidate_dto(candidate: SupplierCandidate) -> CandidateDto:
    supplier = candidate.supplier
    return CandidateDto(
        rank=candidate.rank,
        id=supplier.supplier_id,
        name=supplier.name,
        inn=supplier.inn or "",
        region=supplier.region,
        role=candidate.role,
        role_source=source_dto(candidate.role_evidence),
        status=candidate.status,
        check_reasons=list(candidate.check_reasons),
        matches=[match_dto(match) for match in candidate.matches],
        history=history_dto(candidate.history),
        highlights=[highlight_dto(highlight) for highlight in candidate.highlights],
        score=score_dto(candidate.score),
        contacts=contacts_dto(supplier),
        origins=list(candidate.origins),
        novelty=candidate.novelty,
    )


def pipeline_dto(pipeline: PipelineInfo) -> PipelineDto:
    return PipelineDto(
        version=pipeline.version,
        channels=list(pipeline.channels),
        as_of=pipeline.as_of,
        inputs=list(pipeline.inputs),
        novelty_set=pipeline.novelty_set or None,
    )


def warning_dto(warning: SearchWarning) -> WarningDto:
    return WarningDto(code=warning.code, subject=warning.subject)


def to_response(result: SearchResult) -> SearchResponseDto:
    return SearchResponseDto(
        search_id=result.search_id,
        query=query_dto(result.query),
        items=[item_dto(item) for item in result.items],
        candidates=[candidate_dto(candidate) for candidate in result.candidates],
        pipeline=pipeline_dto(result.pipeline),
        warnings=[warning_dto(warning) for warning in result.warnings],
        created_at=result.created_at,
    )


def to_summary(summary: SearchSummary) -> SearchSummaryDto:
    return SearchSummaryDto(
        search_id=summary.search_id,
        text=summary.text.value,
        locale=summary.locale,
        items=summary.items,
        candidates=summary.candidates,
        recommended=summary.recommended,
        created_at=summary.created_at,
    )
