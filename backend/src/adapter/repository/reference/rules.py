"""Правила нормализации текста из файла."""

from collections.abc import Mapping, Sequence
from typing import Any


class FileTextRules:
    def __init__(
        self,
        months: Mapping[str, str],
        abbreviations: Mapping[str, str],
        synonyms: Mapping[str, str],
        noise: Sequence[str],
        attribute_keys: Mapping[str, str],
        currencies: Mapping[str, str],
    ) -> None:
        self._months = dict(months)
        self._abbreviations = dict(abbreviations)
        self._synonyms = dict(synonyms)
        # Длинные обороты убираются первыми, иначе от них остаются хвосты.
        self._noise = tuple(sorted(noise, key=len, reverse=True))
        self._attribute_keys = dict(attribute_keys)
        self._currencies = dict(currencies)

    @classmethod
    def of(cls, document: Mapping[str, Any]) -> "FileTextRules":
        return cls(
            months=dict(document.get("months", {})),
            abbreviations=dict(document.get("abbreviations", {})),
            synonyms=dict(document.get("synonyms", {})),
            noise=tuple(document.get("noise", ())),
            attribute_keys=dict(document.get("attribute_keys", {})),
            currencies=dict(document.get("currencies", {})),
        )

    @property
    def months(self) -> Mapping[str, str]:
        return self._months

    @property
    def abbreviations(self) -> Mapping[str, str]:
        return self._abbreviations

    @property
    def synonyms(self) -> Mapping[str, str]:
        return self._synonyms

    @property
    def noise(self) -> Sequence[str]:
        return self._noise

    @property
    def attribute_keys(self) -> Mapping[str, str]:
        return self._attribute_keys

    @property
    def currencies(self) -> Mapping[str, str]:
        return self._currencies
