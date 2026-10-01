"""Справочник единиц измерения ОКЕИ из файла."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.adapter.repository.errors import ReferenceDataError

# Непрерывные меры: длина, площадь, объём, масса. Их цену можно делить.
MEASURE_BASES = frozenset({"006", "055", "113", "166", "112"})


@dataclass(frozen=True, slots=True)
class FileUnit:
    code: str
    name: str
    base: str
    factor: float


class FileUnitReference:
    def __init__(self, units: Mapping[str, FileUnit], aliases: Mapping[str, FileUnit]) -> None:
        self._units = dict(units)
        self._aliases = dict(aliases)

    @classmethod
    def of(cls, document: Mapping[str, Any]) -> "FileUnitReference":
        units: dict[str, FileUnit] = {}
        aliases: dict[str, FileUnit] = {}
        for item in document.get("units", ()):
            try:
                unit = FileUnit(
                    code=str(item["code"]),
                    name=str(item["name"]),
                    base=str(item["base"]),
                    factor=float(item["factor"]),
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ReferenceDataError(f"единица измерения описана неверно: {item}") from error
            units[unit.code] = unit
            for alias in (*item.get("aliases", ()), unit.name):
                aliases.setdefault(_key(str(alias)), unit)
        if not units:
            raise ReferenceDataError("справочник единиц измерения пуст")
        return cls(units, aliases)

    def resolve(self, text: str) -> FileUnit | None:
        key = _key(text)
        if not key:
            return None
        return self._aliases.get(key) or self._aliases.get(key.split(" ")[0])

    def is_measure(self, unit: FileUnit) -> bool:
        return unit.base in MEASURE_BASES

    def name_of(self, code: str) -> str:
        unit = self._units.get(code)
        return unit.name if unit else ""


def _key(value: str) -> str:
    return (value or "").strip().strip(".").lower().replace("ё", "е")
