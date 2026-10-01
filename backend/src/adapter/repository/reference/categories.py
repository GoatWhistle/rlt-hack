"""Карта разделов каталогов источников из файла."""

from collections.abc import Mapping
from typing import Any


class FileSourceCategoryReference:
    def __init__(self, providers: Mapping[str, Mapping[str, str]]) -> None:
        self._providers = {
            provider: {_key(category): str(code) for category, code in categories.items()}
            for provider, categories in providers.items()
        }

    @classmethod
    def of(cls, document: Mapping[str, Any]) -> "FileSourceCategoryReference":
        return cls(dict(document.get("providers", {})))

    def code_by_category(self, provider_name: str, category: str) -> str | None:
        return self._providers.get(provider_name, {}).get(_key(category))


def _key(value: str) -> str:
    return " ".join((value or "").split()).lower().replace("ё", "е")
