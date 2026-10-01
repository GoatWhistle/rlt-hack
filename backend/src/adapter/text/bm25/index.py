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
        self._counts = [Counter(document) for document in documents]
        self._lengths = [len(document) for document in documents]
        total = sum(self._lengths)
        self._average = total / len(documents) if total else 1.0
        self._frequency: Counter[str] = Counter()
        for counts in self._counts:
            self._frequency.update(counts.keys())
        self._k1 = k1
        self._b = b

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

    def _score(self, counts: Counter[str], length: int, weights: dict[str, float]) -> float:
        norm = self._k1 * (1 - self._b + self._b * length / self._average)
        total = 0.0
        for term, weight in weights.items():
            frequency = counts[term]
            if frequency:
                total += weight * frequency * (self._k1 + 1) / (frequency + norm)
        return total
