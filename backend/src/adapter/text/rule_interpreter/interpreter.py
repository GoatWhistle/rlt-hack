import re
from dataclasses import dataclass

from src.adapter.text.rule_interpreter.okpd2 import extract_okpd2
from src.adapter.text.rule_interpreter.protocols import TextAnalyzer
from src.adapter.text.rule_interpreter.quantity import extract_quantity
from src.adapter.text.rule_interpreter.splitter import split_positions
from src.models.enums import ItemOrigin, ItemType
from src.models.query_item import Quantity, QueryItem
from src.models.requirement import Requirement, extract_requirements
from src.models.search import SearchQuery

EDGE_PUNCTUATION = " \t,.;:-–—*()[]{}\"'«»"
SERVICE_PREFIXES = ("доставк", "срок", "оплат", "адрес", "контакт", "телефон")
MAX_ITEMS = 50


@dataclass(frozen=True, slots=True)
class ParsedPosition:
    name: str
    okpd2: str = ""
    quantity: Quantity | None = None
    requirements: tuple[Requirement, ...] = ()


class RuleQueryInterpreter:
    def __init__(self, analyzer: TextAnalyzer, max_items: int = MAX_ITEMS) -> None:
        self._analyzer = analyzer
        self._max_items = max_items

    async def interpret(self, query: SearchQuery) -> tuple[QueryItem, ...]:
        text = query.text.value
        positions = [
            parsed
            for segment in split_positions(text)
            if not _is_service_note(segment) and (parsed := self._parse(segment)) is not None
        ]
        if not positions:
            whole = self._parse(text)
            positions = [whole] if whole is not None else []
        item_type = query.filters.item_type or ItemType.UNKNOWN
        return tuple(
            QueryItem(
                item_id=f"i{number}",
                name=position.name,
                origin=ItemOrigin.TEXT,
                okpd2=position.okpd2,
                item_type=item_type,
                quantity=position.quantity,
                requirements=position.requirements,
            )
            for number, position in enumerate(positions[: self._max_items], start=1)
        )

    def _parse(self, segment: str) -> ParsedPosition | None:
        quantity, rest = extract_quantity(segment)
        okpd2, rest = extract_okpd2(rest)
        name = " ".join(rest.split()).strip(EDGE_PUNCTUATION)
        if not name or not self._analyzer.analyze(name):
            return None
        return ParsedPosition(
            name=name[0].upper() + name[1:],
            okpd2=okpd2,
            quantity=quantity,
            requirements=extract_requirements(rest),
        )


def _is_service_note(segment: str) -> bool:
    first = re.split(r"\s+", segment.strip().lower(), maxsplit=1)[0]
    return first.startswith(SERVICE_PREFIXES)
