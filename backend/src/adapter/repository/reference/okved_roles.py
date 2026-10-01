"""Роли компаний по префиксам ОКВЭД из файла."""

from collections.abc import Mapping
from typing import Any

from src.adapter.repository.errors import ReferenceDataError
from src.models.enums import SupplierRole


class FileOkvedRoles:
    def __init__(self, prefixes: Mapping[str, SupplierRole], version: str) -> None:
        self._prefixes = dict(prefixes)
        self._version = version

    @classmethod
    def of(cls, document: Mapping[str, Any]) -> "FileOkvedRoles":
        prefixes: dict[str, SupplierRole] = {}
        for entry in document.get("roles", []):
            try:
                role = SupplierRole(entry["role"])
            except (KeyError, ValueError) as error:
                raise ReferenceDataError(f"okved_roles.json: неверная роль {entry!r}") from error
            for prefix in entry.get("prefixes", []):
                digits = _digits(prefix)
                if not digits or digits in prefixes:
                    raise ReferenceDataError(f"okved_roles.json: неверный префикс {prefix!r}")
                prefixes[digits] = role
        return cls(prefixes, str(document.get("version", "")))

    @property
    def version(self) -> str:
        return self._version

    def role_by_okved(self, code: str) -> SupplierRole | None:
        """Самый длинный префикс выигрывает: 45.20 — ремонт (45.2), а не торговля 45.

        Сравниваются цифры кода: подкласс 45.2 — префикс группы 45.20, хотя
        сегменты между точками у них разные.
        """
        digits = _digits(code)
        for length in range(len(digits), 1, -1):
            role = self._prefixes.get(digits[:length])
            if role is not None:
                return role
        return None


def _digits(code: str) -> str:
    return "".join(char for char in code if char.isdigit())
