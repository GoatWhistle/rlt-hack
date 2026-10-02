import math
from collections import Counter
from collections.abc import Sequence

DEFAULT_K1 = 1.2
DEFAULT_B = 0.75


class Bm25Index:
    def __init__(
        self,
        documents: Sequence[Sequence[str]],
        k1: float = DEFAULT_K1,
        b: float = DEFAULT_B,
    ) -> None:
        self._k1 = k1
        self._b = b
        self._counts: list[Counter[str]] = []
        self._lengths: list[int] = []
        self._average = 1.0
        self._frequency: Counter[str] = Counter()
        self._index([Counter(document) for document in documents])

    @classmethod
    def of_counts(
        cls,
        counts: Sequence[Counter[str]],
        lengths: Sequence[int] | None = None,
        k1: float = DEFAULT_K1,
        b: float = DEFAULT_B,
    ) -> "Bm25Index":
        index = cls((), k1, b)
        index._index(list(counts), lengths)
        return index

    def __len__(self) -> int:
        return len(self._counts)

    def idf(self, term: str) -> float:
        size = len(self._counts)
        frequency = self._frequency[term]
        return math.log(1 + (size - frequency + 0.5) / (frequency + 0.5))

    def scores(self, query: Sequence[str]) -> list[float]:
        terms = tuple(dict.fromkeys(query))
        weights = {term: self.idf(term) for term in terms if self._frequency[term]}
        return [
            self._score(counts, length, weights)
            for counts, length in zip(self._counts, self._lengths, strict=True)
        ]

    def _index(self, counts: list[Counter[str]], lengths: Sequence[int] | None = None) -> None:
        if lengths is not None and len(lengths) != len(counts):
            raise ValueError("every document needs a length")
        self._counts = counts
        self._lengths = (
            [document.total() for document in counts]
            if lengths is None
            else [
                max(length, document.total())
                for length, document in zip(lengths, counts, strict=True)
            ]
        )
        total = sum(self._lengths)
        self._average = total / len(counts) if total else 1.0
        self._frequency = Counter()
        for document in counts:
            self._frequency.update(document.keys())

    def _score(self, counts: Counter[str], length: int, weights: dict[str, float]) -> float:
        norm = self._k1 * (1 - self._b + self._b * length / self._average)
        total = 0.0
        for term, weight in weights.items():
            frequency = counts[term]
            if frequency:
                total += weight * frequency * (self._k1 + 1) / (frequency + norm)
        return total
