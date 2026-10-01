from collections.abc import Sequence

from src.adapter.repository.clickhouse.retrieval.protocols import TextAnalyzer
from src.adapter.text.bm25.index import Bm25Index

MIN_NEEDLE_LENGTH = 3
MAX_NEEDLES = 64


def normalized(column: str) -> str:
    return f"replaceAll(lowerUTF8({column}), 'ё', 'е')"


def needles_for(analyzer: TextAnalyzer, text: str) -> tuple[str, ...]:
    prefixes = analyzer.prefixes(text)
    return tuple(prefix for prefix in prefixes if len(prefix) >= MIN_NEEDLE_LENGTH)[:MAX_NEEDLES]


def relevance(analyzer: TextAnalyzer, query: str, texts: Sequence[str]) -> list[float]:
    stems = analyzer.analyze(query)
    if not stems or not texts:
        return [0.0] * len(texts)
    return Bm25Index([analyzer.analyze(text) for text in texts]).scores(stems)
