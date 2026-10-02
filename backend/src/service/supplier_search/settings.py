from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    fusion: float = 0.4
    coverage: float = 0.3
    evidence: float = 0.2
    history: float = 0.1

    def __post_init__(self) -> None:
        weights = (self.fusion, self.coverage, self.evidence, self.history)
        if any(weight < 0 for weight in weights) or sum(weights) <= 0:
            raise ValueError("weights must be non-negative and not all zero")

    @property
    def total(self) -> float:
        return self.fusion + self.coverage + self.evidence + self.history


@dataclass(frozen=True, slots=True)
class SearchSettings:
    pipeline_version: str = "search-v1"
    timeout_seconds: float = 8.0
    archive_timeout_seconds: float = 2.0
    retrieval_depth_factor: int = 3
    rrf_k: int = 60
    coverage_threshold: float = 0.5
    offers_per_supplier: int = 20
    history_records: int = 5
    context_channels: tuple[str, ...] = ()
    weights: ScoreWeights = field(default_factory=ScoreWeights)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.archive_timeout_seconds <= 0:
            raise ValueError("timeouts must be positive")
        if self.retrieval_depth_factor < 1 or self.rrf_k < 1:
            raise ValueError("retrieval depth and rrf k must be positive")
        if not 0 < self.coverage_threshold <= 1:
            raise ValueError("coverage threshold must be within (0, 1]")

    def retrieval_depth(self, limit: int) -> int:
        return limit * self.retrieval_depth_factor
