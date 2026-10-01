"""Словарь головных слов из файла: слово или сочетание — код ОКПД2.

Ключи записаны по-человечески, в именительном падеже. Основы слов считает та же
функция, что и при разборе названия, поэтому словарь и позиция сравниваются
одинаково.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from src.adapter.repository.errors import ReferenceDataError


class FileLexicon:
    def __init__(self, entries: Sequence[tuple[tuple[str, ...], str]]) -> None:
        self._entries = tuple(entries)

    @classmethod
    def of(
        cls,
        document: Mapping[str, Any],
        word_stems: Callable[[str], tuple[str, ...]],
    ) -> "FileLexicon":
        entries: list[tuple[tuple[str, ...], str]] = []
        for phrase, code in dict(document.get("entries", {})).items():
            key = word_stems(str(phrase))
            if not key:
                raise ReferenceDataError(f"запись словаря без основы: {phrase}")
            entries.append((key, str(code)))
        if not entries:
            raise ReferenceDataError("словарь головных слов пуст")
        # Длинные сочетания проверяются первыми: они точнее одиночного слова.
        entries.sort(key=lambda item: len(item[0]), reverse=True)
        return cls(entries)

    @property
    def entries(self) -> Sequence[tuple[tuple[str, ...], str]]:
        return self._entries
