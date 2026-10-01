"""Справочник ОКПД2 из файла: наименования классов и отобранных групп.

Индекс названий строится той же функцией ключа, что и запрос классификатора:
обе стороны сравнения обязаны считаться одинаково.
"""

from collections.abc import Callable, Mapping
from typing import Any

from src.adapter.repository.errors import ReferenceDataError


class FileOkpd2Reference:
    def __init__(self, names: Mapping[str, str], index: Mapping[str, str]) -> None:
        self._names = dict(names)
        self._index = dict(index)

    @classmethod
    def of(cls, document: Mapping[str, Any], key: Callable[[str], str]) -> "FileOkpd2Reference":
        names: dict[str, str] = {}
        for section in ("classes", "groups"):
            for code, name in dict(document.get(section, {})).items():
                names[str(code)] = str(name)
        if not names:
            raise ReferenceDataError("справочник ОКПД2 пуст")
        index: dict[str, str] = {}
        for code, name in names.items():
            # Одно название на два кода — повод не отдавать ни одного.
            index[key(name)] = "" if key(name) in index else code
        return cls(names, {name: code for name, code in index.items() if code})

    def code_by_name(self, normalized_name: str) -> str | None:
        return self._index.get(normalized_name)

    def name_of(self, code: str) -> str:
        """Название кода, а если его нет — ближайшего известного уровня."""
        for candidate in (code, code[:5], code[:2]):
            name = self._names.get(candidate)
            if name:
                return name
        return ""

    def has_class(self, code: str) -> bool:
        return code[:2] in self._names

    def classes(self) -> tuple[str, ...]:
        """Коды классов: по ним сверяется полнота рубрик и типов."""
        return tuple(code for code in self._names if len(code) == 2)
