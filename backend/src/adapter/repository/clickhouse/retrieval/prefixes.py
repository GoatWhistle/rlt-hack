from collections.abc import Sequence
from dataclasses import dataclass, field

TOKEN_SEPARATOR = "[^0-9a-zа-я]+"
PREFIX_LENGTHS = (3, 4, 5, 6)
MIN_TERM_LENGTH = PREFIX_LENGTHS[0]
MAX_PREFIX_LENGTH = PREFIX_LENGTHS[-1]
FLAGS = "flags"


def _tokens(column: str) -> str:
    return f"splitByRegexp('{TOKEN_SEPARATOR}', {column})"


def prefix_terms(column: str) -> str:
    prefixes = ", ".join(f"leftUTF8(t, {length})" for length in PREFIX_LENGTHS)
    return (
        f"arrayDistinct(arrayFlatten(arrayMap(t -> [{prefixes}], "
        f"arrayFilter(t -> lengthUTF8(t) >= {MIN_TERM_LENGTH}, {_tokens(column)}))))"
    )


def term_count(column: str) -> str:
    return f"toUInt16(least(65535, length(arrayFilter(t -> t != '', {_tokens(column)}))))"


@dataclass(frozen=True, slots=True)
class TermMatch:
    columns: str
    matched: str
    hits: str
    parameters: dict[str, object] = field(default_factory=dict)


def term_match(column: str, terms: Sequence[str]) -> TermMatch:
    if not terms:
        raise ValueError("at least one term is required")
    expression = prefix_terms(column)
    names = [f"term_{index}" for index in range(len(terms))]
    flags = ", ".join(
        f"hasAnyTokens({expression}, [{{{name}:String}}]) AS {name}" for name in names
    )
    return TermMatch(
        columns=f"{flags}, [{', '.join(names)}] AS {FLAGS}",
        matched="(" + " OR ".join(names) + ")",
        hits="(" + " + ".join(names) + ")",
        parameters=dict(zip(names, terms, strict=True)),
    )
