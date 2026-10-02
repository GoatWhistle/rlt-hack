from collections import Counter
from collections.abc import Sequence

from src.adapter.repository.clickhouse.search.retrieval.prefixes import (
    MAX_PREFIX_LENGTH,
    MIN_TERM_LENGTH,
)
from src.adapter.repository.clickhouse.search.retrieval.protocols import TextAnalyzer
from src.adapter.text.bm25.index import Bm25Index

MAX_TERMS = 64


def index_terms(analyzer: TextAnalyzer, text: str) -> tuple[str, ...]:
    prefixes = (prefix[:MAX_PREFIX_LENGTH] for prefix in analyzer.prefixes(text))
    terms = dict.fromkeys(prefix for prefix in prefixes if len(prefix) >= MIN_TERM_LENGTH)
    return tuple(terms)[:MAX_TERMS]


def flags_of(value: object) -> tuple[bool, ...]:
    if not isinstance(value, list | tuple):
        raise TypeError(value)
    return tuple(flag if isinstance(flag, bool) else bool(int(str(flag))) for flag in value)


def match_share(flags: Sequence[bool]) -> float:
    return sum(flags) / len(flags) if flags else 0.0


def presence_relevance(flags: Sequence[Sequence[bool]], lengths: Sequence[int]) -> list[float]:
    if not flags:
        return []
    width = max(len(row) for row in flags)
    counts = [
        Counter({str(index): 1 for index, present in enumerate(row) if present}) for row in flags
    ]
    index = Bm25Index.of_counts(counts, lengths)
    return index.scores([str(term) for term in range(width)])
