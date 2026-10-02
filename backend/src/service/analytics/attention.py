"""Приоритетные проблемы среза: причина, масштаб и куда смотреть."""

from src.models.analytics.slice import AnalyticsSlice, ProblemRow, SourceRow
from src.models.analytics.view import AttentionCode, AttentionItem
from src.models.enums import FetchStatus

ATTENTION_LIMIT = 5
STALE_SHARE = 0.5
UNCLASSIFIED_SHARE = 0.3


def attention_items(snapshot: AnalyticsSlice) -> tuple[AttentionItem, ...]:
    problems = {row.source_id: row for row in snapshot.problems}
    found: list[AttentionItem] = []
    for source in snapshot.sources:
        found.extend(_source_items(source, problems.get(source.source_id)))
    found.extend(_catalog_items(snapshot))
    found.sort(key=lambda item: (_RANK[item.code], -item.count))
    return tuple(found[:ATTENTION_LIMIT])


def _source_items(source: SourceRow, problem: ProblemRow | None) -> list[AttentionItem]:
    if source.last_attempt_at is None:
        return [AttentionItem(AttentionCode.SOURCE_NEVER_RUN, source.source_id, 0, 0)]
    items: list[AttentionItem] = []
    if source.last_attempt_status == FetchStatus.FAILED:
        items.append(AttentionItem(AttentionCode.SOURCE_FAILED, source.source_id, 1, 1))
    if source.offers and problem is not None and problem.stale / source.offers >= STALE_SHARE:
        items.append(
            AttentionItem(
                AttentionCode.SOURCE_STALE, source.source_id, problem.stale, source.offers
            )
        )
    return items


def _catalog_items(snapshot: AnalyticsSlice) -> list[AttentionItem]:
    items: list[AttentionItem] = []
    missing = sum(row.no_category for row in snapshot.problems)
    if snapshot.offers and missing / snapshot.offers >= UNCLASSIFIED_SHARE:
        items.append(AttentionItem(AttentionCode.NO_CATEGORY, None, missing, snapshot.offers))
    unverified = sum(row.unverified_seller + row.no_supplier for row in snapshot.problems)
    if snapshot.offers and unverified == snapshot.offers:
        items.append(
            AttentionItem(AttentionCode.NO_VERIFIED_SELLER, None, unverified, snapshot.offers)
        )
    return items


_RANK = {
    AttentionCode.SOURCE_FAILED: 0,
    AttentionCode.SOURCE_NEVER_RUN: 1,
    AttentionCode.SOURCE_STALE: 2,
    AttentionCode.NO_CATEGORY: 3,
    AttentionCode.NO_VERIFIED_SELLER: 4,
}
