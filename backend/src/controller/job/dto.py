"""DTO команды синхронизации: разобранные аргументы командной строки."""

import argparse
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SyncCommand:
    """Что запросил оператор джобы."""

    forever: bool = False
    parallel_sources: int | None = None

    @classmethod
    def of(cls, arguments: argparse.Namespace) -> "SyncCommand":
        return cls(forever=bool(arguments.forever), parallel_sources=arguments.parallel)
