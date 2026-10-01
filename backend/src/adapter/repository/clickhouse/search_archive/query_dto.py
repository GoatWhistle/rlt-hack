from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict

from src.models.enums import ItemOrigin, ItemType, Locale
from src.models.query_item import Quantity, QueryItem
from src.models.search import CandidateLimit, SearchFilters, SearchQuery, SearchText


class FrozenDto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantityDto(FrozenDto):
    value: Decimal
    unit: str

    @classmethod
    def from_domain(cls, quantity: Quantity) -> Self:
        return cls(value=quantity.value, unit=quantity.unit)

    def to_domain(self) -> Quantity:
        return Quantity(value=self.value, unit=self.unit)


class QueryItemDto(FrozenDto):
    item_id: str
    name: str
    origin: ItemOrigin
    okpd2: str
    item_type: ItemType
    quantity: QuantityDto | None

    @classmethod
    def from_domain(cls, item: QueryItem) -> Self:
        return cls(
            item_id=item.item_id,
            name=item.name,
            origin=item.origin,
            okpd2=item.okpd2,
            item_type=item.item_type,
            quantity=None if item.quantity is None else QuantityDto.from_domain(item.quantity),
        )

    def to_domain(self) -> QueryItem:
        return QueryItem(
            item_id=self.item_id,
            name=self.name,
            origin=self.origin,
            okpd2=self.okpd2,
            item_type=self.item_type,
            quantity=None if self.quantity is None else self.quantity.to_domain(),
        )


class QueryDto(FrozenDto):
    text: str
    limit: int
    locale: Locale
    regions: tuple[str, ...]
    item_type: ItemType | None

    @classmethod
    def from_domain(cls, query: SearchQuery) -> Self:
        return cls(
            text=query.text.value,
            limit=query.limit.value,
            locale=query.locale,
            regions=query.filters.regions,
            item_type=query.filters.item_type,
        )

    def to_domain(self) -> SearchQuery:
        return SearchQuery(
            text=SearchText(self.text),
            limit=CandidateLimit(self.limit),
            locale=self.locale,
            filters=SearchFilters(regions=self.regions, item_type=self.item_type),
        )
