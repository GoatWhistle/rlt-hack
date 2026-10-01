"""Чистка текста и приведение слов к сравнимому виду.

Здесь только чистые функции: словари правил приходят параметрами, поэтому
модуль ничего не знает ни о файлах справочников, ни о хранилище. Лемматизатора
со словарём намеренно нет — основа слова отрезается правилами, чтобы разбор
оставался детерминированным и не тянул внешних данных.
"""

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence

# Окончания отрезаются от длинного к короткому: первое подходящее выигрывает.
ENDINGS = (
    "ами",
    "ями",
    "ого",
    "его",
    "ому",
    "ему",
    "ыми",
    "ими",
    "ость",
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ой",
    "ей",
    "ый",
    "ий",
    "ам",
    "ям",
    "ах",
    "ях",
    "ов",
    "ев",
    "ью",
    "ом",
    "ем",
    "а",
    "я",
    "ы",
    "и",
    "е",
    "о",
    "у",
    "ю",
    "ь",
    "й",
)
MIN_STEM = 4

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES = re.compile(r"\s+")
_WORD = re.compile(r"[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z-]*|\d+(?:[.,]\d+)?")
# Excel портит числа в обе стороны: «1.79» становится «янв.79», а «10.6» — «10.июн».
_EXCEL_MONTH_FIRST = re.compile(r"\b([А-Яа-я]{3})\.(\d+)\b")
_EXCEL_MONTH_LAST = re.compile(r"\b(\d+)\.([А-Яа-я]{3})\b")


def clean(value: str) -> str:
    """Убирает невидимый мусор, выравнивает пробелы и форму символов."""
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace(" ", " ").replace("\u200b", "")
    return _SPACES.sub(" ", _CONTROL.sub(" ", text)).strip()


def fix_numbers(value: str, months: Mapping[str, str]) -> str:
    """Лечит числа, испорченные Excel.

    «янв.79» снова становится «1.79», а «10.июн» — «10.6»: месяц мог оказаться
    и в начале, и в конце в зависимости от того, как Excel прочитал исходное
    число.
    """

    def month_first(match: re.Match[str]) -> str:
        month = months.get(match.group(1).lower())
        return f"{month}.{match.group(2)}" if month else match.group(0)

    def month_last(match: re.Match[str]) -> str:
        month = months.get(match.group(2).lower())
        return f"{match.group(1)}.{month}" if month else match.group(0)

    return _EXCEL_MONTH_LAST.sub(month_last, _EXCEL_MONTH_FIRST.sub(month_first, value))


def tokens(value: str) -> list[str]:
    """Слова и числа названия в нижнем регистре, с «ё» сведённой к «е»."""
    return [token.lower().replace("ё", "е") for token in _WORD.findall(value)]


def stem(word: str) -> str:
    """Отрезает окончание, пока основа остаётся узнаваемой."""
    lowered = word.lower().replace("ё", "е")
    for ending in ENDINGS:
        if lowered.endswith(ending) and len(lowered) - len(ending) >= MIN_STEM:
            return lowered[: -len(ending)]
    return lowered


def stems(value: str) -> tuple[str, ...]:
    return tuple(stem(token) for token in tokens(value))


def expand(value: str, abbreviations: Mapping[str, str], synonyms: Mapping[str, str]) -> str:
    """Раскрывает сокращения и сводит синонимы к одному слову."""
    result = []
    for token in _WORD.findall(value):
        lowered = token.lower().replace("ё", "е")
        replacement = abbreviations.get(lowered) or synonyms.get(lowered)
        result.append(replacement if replacement else token)
    return " ".join(result)


def drop_noise(value: str, noise: Iterable[str]) -> str:
    """Убирает рекламные обороты: они не описывают предмет."""
    text = value
    for phrase in noise:
        text = re.sub(rf"\b{re.escape(phrase)}\b", " ", text, flags=re.IGNORECASE)
    return _SPACES.sub(" ", text).strip(" ,.;-")


def contains(haystack: Sequence[str], needle: Sequence[str]) -> int:
    """Позиция последовательности основ внутри другой или -1."""
    if not needle or len(needle) > len(haystack):
        return -1
    for start in range(len(haystack) - len(needle) + 1):
        if tuple(haystack[start : start + len(needle)]) == tuple(needle):
            return start
    return -1
