from decimal import Decimal, InvalidOperation

from src.controller.search.dto import (
    ContextDto,
    FilterItemType,
    FiltersDto,
    QueryDto,
    SearchRequestDto,
)
from src.models.enums import ItemType, Locale
from src.models.errors import InvalidSearchContextError
from src.models.search import (
    CandidateLimit,
    SearchContext,
    SearchFilters,
    SearchQuery,
    SearchText,
)

FILTER_ITEM_TYPES: dict[ItemType, FilterItemType] = {
    ItemType.GOODS: "goods",
    ItemType.WORK: "work",
    ItemType.SERVICE: "service",
}


def to_context(dto: ContextDto) -> SearchContext:
    raw_price = (dto.start_price or "").replace(" ", "").replace(",", ".")
    try:
        price = Decimal(raw_price) if raw_price else None
    except InvalidOperation as error:
        raise InvalidSearchContextError("start price is not a number") from error
    return SearchContext(customer_inn=dto.customer_inn or "", start_price=price)


def to_query(dto: SearchRequestDto, locale: Locale) -> SearchQuery:
    item_type = dto.filters.item_type
    return SearchQuery(
        text=SearchText(dto.text),
        limit=CandidateLimit.default() if dto.limit is None else CandidateLimit(dto.limit),
        locale=locale,
        filters=SearchFilters(
            regions=tuple(dto.filters.regions),
            item_type=None if item_type is None else ItemType(item_type),
        ),
        context=to_context(dto.context),
    )


def context_dto(context: SearchContext) -> ContextDto:
    price = context.start_price
    return ContextDto(
        customer_inn=context.customer_inn or None,
        start_price=None if price is None else format(price, "f"),
    )


def query_dto(query: SearchQuery) -> QueryDto:
    item_type = query.filters.item_type
    return QueryDto(
        text=query.text.value,
        locale=query.locale,
        limit=query.limit.value,
        filters=FiltersDto(
            regions=list(query.filters.regions),
            item_type=None if item_type is None else FILTER_ITEM_TYPES.get(item_type),
        ),
        context=context_dto(query.context),
        origin=query.origin,
    )
