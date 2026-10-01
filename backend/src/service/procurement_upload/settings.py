from dataclasses import dataclass

from src.models.search import CandidateLimit


@dataclass(frozen=True, slots=True)
class UploadSettings:
    max_rows: int = 5000
    candidates_per_lot: int = CandidateLimit.DEFAULT
    concurrency: int = 4
    attempts: int = 3
    retry_delay_seconds: float = 1.0
    lot_timeout_seconds: float = 30.0
    resume_delay_seconds: float = 5.0
    max_selected_lots: int = 5000

    def __post_init__(self) -> None:
        if min(self.max_rows, self.concurrency, self.attempts, self.max_selected_lots) < 1:
            raise ValueError("rows, concurrency, attempts and selection must be positive")
        if not CandidateLimit.MIN <= self.candidates_per_lot <= CandidateLimit.MAX:
            raise ValueError("candidates per lot must fit the candidate limit")
        if self.lot_timeout_seconds <= 0:
            raise ValueError("lot timeout must be positive")
        if self.retry_delay_seconds < 0 or self.resume_delay_seconds < 0:
            raise ValueError("delays cannot be negative")
