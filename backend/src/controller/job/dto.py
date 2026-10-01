"""DTO команд джобы: разобранные аргументы командной строки."""

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SyncCommand:
    """Что запросил оператор джобы."""

    forever: bool = False
    parallel_sources: int | None = None

    @classmethod
    def of(cls, arguments: argparse.Namespace) -> "SyncCommand":
        return cls(forever=bool(arguments.forever), parallel_sources=arguments.parallel)


@dataclass(frozen=True, slots=True)
class NormalizeCommand:
    """Сколько сохранённых позиций пересчитать."""

    limit: int | None = None

    @classmethod
    def of(cls, arguments: argparse.Namespace) -> "NormalizeCommand":
        limit = arguments.limit
        return cls(limit=limit if limit is None or limit > 0 else None)


@dataclass(frozen=True, slots=True)
class RegistryImportCommand:
    """Откуда читать выгрузку реестра МСП: аргумент важнее настройки окружения."""

    path: Path | None = None

    @classmethod
    def of(cls, arguments: argparse.Namespace, default: Path | None) -> "RegistryImportCommand":
        return cls(path=Path(arguments.path).expanduser() if arguments.path else default)
