"""Разбор названия: предмет отдельно, бренд, артикул и размеры отдельно.

Название у поставщика — это обычно всё сразу: предмет, бренд, габариты, ГОСТ и
артикул одной строкой. Разбор вытаскивает узнаваемые части в поля, а в ядре
оставляет сам предмет — по нему идут склейка дублей и поиск головного слова.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from src.service.normalizer.protocols import TextRules
from src.service.normalizer.text import clean, drop_noise, expand, fix_numbers

_GOST = re.compile(r"\bГОСТ\s*[Рр]?\s*[\d][\d.\-/]*", re.IGNORECASE)
_TU = re.compile(r"\bТУ\s*[\d][\d.\-/]*", re.IGNORECASE)
_ARTICLE_TAIL = re.compile(r"[\s,]+(\d{4,})\s*$")
_ARTICLE_LABEL = re.compile(
    r"\bарт(?:икул)?\.?\s*[:№]?\s*([A-Za-zА-Яа-я0-9][\w\-/]*)", re.IGNORECASE
)
_MEASURES = (
    ("voltage_v", re.compile(r"(\d+(?:[.,]\d+)?)\s*В\b")),
    ("power_w", re.compile(r"(\d+(?:[.,]\d+)?)\s*Вт\b")),
    ("length_mm", re.compile(r"(\d+(?:[.,]\d+)?)\s*мм\b", re.IGNORECASE)),
    ("length_m", re.compile(r"(\d+(?:[.,]\d+)?)\s*м\b")),
    ("weight_kg", re.compile(r"(\d+(?:[.,]\d+)?)\s*кг\b", re.IGNORECASE)),
    ("volume_l", re.compile(r"(\d+(?:[.,]\d+)?)\s*л\b", re.IGNORECASE)),
)
_PUNCTUATION = re.compile(r"[(),;«»\"']+")
_DANGLING = re.compile(r"\s+[-–—/\\]\s*$|^\s*[-–—/\\]\s+")


@dataclass(frozen=True, slots=True)
class NameParts:
    core: str
    brand: str = ""
    article: str = ""
    attributes: dict[str, str] = field(default_factory=dict)


def decompose(name: str, rules: TextRules, brand: str = "", article: str = "") -> NameParts:
    """Делит название на предмет, бренд, артикул и найденные размеры."""
    text = fix_numbers(clean(name), rules.months)
    found: dict[str, str] = {}
    text = _take(text, _GOST, lambda value: found.setdefault("gost", value.strip()))
    text = _take(text, _TU, lambda value: found.setdefault("tu", value.strip()))

    label = _ARTICLE_LABEL.search(text)
    if label:
        article = article or label.group(1)
        text = text.replace(label.group(0), " ")
    tail = _ARTICLE_TAIL.search(text)
    if tail:
        article = article or tail.group(1)
        text = text[: tail.start()]

    for key, pattern in _MEASURES:
        match = pattern.search(text)
        if match:
            found.setdefault(key, match.group(1).replace(",", "."))

    if brand:
        text = re.sub(rf"\b{re.escape(brand)}\b", " ", text, flags=re.IGNORECASE)
    core = expand(text, rules.abbreviations, rules.synonyms)
    core = drop_noise(_PUNCTUATION.sub(" ", core), rules.noise)
    core = _DANGLING.sub("", core).strip(" .,-–—/").lower()
    if not core:
        # Название целиком из рекламных слов — «ОПТОМ». Пустое ядро хуже
        # бесполезного: по нему не склеить дубли и не найти позицию.
        core = _PUNCTUATION.sub(" ", text).strip(" .,-–—/").lower()
    return NameParts(
        core=clean(core),
        brand=brand.strip(),
        article=article.strip(),
        attributes=found,
    )


def _take(text: str, pattern: re.Pattern[str], keep: Callable[[str], None]) -> str:
    """Вынимает совпадение из текста и отдаёт его обработчику."""
    match = pattern.search(text)
    if not match:
        return text
    keep(match.group(0))
    return text.replace(match.group(0), " ")
