"""Справочник рубрик и правил типа позиции из файла."""

from collections.abc import Mapping, Sequence
from typing import Any

from src.adapter.repository.errors import ReferenceDataError


class FileRubricReference:
    def __init__(
        self,
        prefixes: Mapping[str, str],
        names: Mapping[str, str],
        class_types: Mapping[str, str],
        type_phrases: Mapping[str, Sequence[str]],
    ) -> None:
        self._prefixes = dict(prefixes)
        self._names = dict(names)
        self._class_types = dict(class_types)
        self._type_phrases = {name: tuple(items) for name, items in type_phrases.items()}

    @classmethod
    def of(cls, document: Mapping[str, Any]) -> "FileRubricReference":
        prefixes: dict[str, str] = {}
        names: dict[str, str] = {}
        for rubric in document.get("rubrics", ()):
            code = str(rubric.get("code", ""))
            if not code:
                raise ReferenceDataError(f"рубрика без кода: {rubric}")
            names[code] = str(rubric.get("name", code))
            for prefix in rubric.get("prefixes", ()):
                if str(prefix) in prefixes:
                    raise ReferenceDataError(f"префикс {prefix} отдан двум рубрикам")
                prefixes[str(prefix)] = code
        class_types = {
            str(item): name
            for name, items in dict(document.get("item_type", {})).items()
            for item in items
        }
        if not prefixes or not class_types:
            raise ReferenceDataError("справочник рубрик неполон")
        return cls(prefixes, names, class_types, dict(document.get("phrases", {})))

    @property
    def prefixes(self) -> Mapping[str, str]:
        return self._prefixes

    @property
    def names(self) -> Mapping[str, str]:
        return self._names

    @property
    def class_types(self) -> Mapping[str, str]:
        return self._class_types

    @property
    def type_phrases(self) -> Mapping[str, Sequence[str]]:
        return self._type_phrases
