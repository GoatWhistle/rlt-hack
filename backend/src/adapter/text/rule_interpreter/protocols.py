from typing import Protocol


class TextAnalyzer(Protocol):
    def analyze(self, text: str) -> tuple[str, ...]: ...
