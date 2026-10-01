"""Каналы классификации в порядке надёжности.

Каждый канал либо возвращает код с основанием, либо ничего. Угадывание
запрещено: если не сработал ни один канал, позиция остаётся без кода и попадает
в отчёт о покрытии.
"""

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from src.models.enums import ClassificationMethod
from src.service.classifier.protocols import (
    LexiconReference,
    Okpd2Reference,
    SourceCategoryReference,
)
from src.service.classifier.taxonomy import normalize_code
from src.service.normalizer.text import contains

# Головное слово стоит в начале названия: «картридж» в конце описания лекарства
# предметом не является. Окно задаётся в основах слов.
HEAD_WINDOW = 4

CONFIDENCE = {
    ClassificationMethod.GOLD: 1.0,
    ClassificationMethod.REFERENCE: 0.9,
    ClassificationMethod.ARCHIVE: 0.8,
    ClassificationMethod.SOURCE_MAP: 0.7,
    ClassificationMethod.LEXICON: 0.6,
}


class Hit(NamedTuple):
    code: str
    method: ClassificationMethod
    evidence: str

    @property
    def confidence(self) -> float:
        return CONFIDENCE[self.method]


def gold(code: str, source_name: str) -> Hit | None:
    """Код пришёл из самого источника или архива: его не пересчитывают."""
    valid = normalize_code(code)
    return Hit(valid, ClassificationMethod.GOLD, f"код источника {source_name}") if valid else None


def by_reference(key: str, name: str, reference: Okpd2Reference) -> Hit | None:
    """Название дословно совпало с наименованием из справочника ОКПД2."""
    code = reference.code_by_name(key) if key else None
    if not code:
        return None
    return Hit(code, ClassificationMethod.REFERENCE, f"наименование ОКПД2: {name}")


def by_archive(key: str, name: str, index: Mapping[str, str]) -> Hit | None:
    """Такое же название встречалось в архиве закупок с проставленным кодом."""
    code = index.get(key) if key else None
    return Hit(code, ClassificationMethod.ARCHIVE, f"позиция архива: {name}") if code else None


def by_source_category(
    provider_name: str,
    category: str,
    reference: SourceCategoryReference,
) -> Hit | None:
    """Раздел каталога источника отображён на код вручную."""
    code = reference.code_by_category(provider_name, category) if category else None
    if not code:
        return None
    return Hit(code, ClassificationMethod.SOURCE_MAP, f"раздел каталога: {category}")


def by_lexicon(
    stems: Sequence[str],
    lexicon: LexiconReference,
    window: int = HEAD_WINDOW,
) -> Hit | None:
    """Головное слово или сочетание из словаря.

    Слово ищется только в начале названия и выигрывает самое длинное
    сочетание, а при равной длине — стоящее раньше: в «сверло по стеклу»
    предмет — сверло, а не стекло.
    """
    best: tuple[int, int, tuple[str, ...], str] | None = None
    for phrase, code in lexicon.entries:
        position = contains(stems, phrase)
        if position < 0 or position >= window:
            continue
        candidate = (-len(phrase), position, phrase, code)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    if best is None:
        return None
    return Hit(best[3], ClassificationMethod.LEXICON, f"словарь: {' '.join(best[2])}")
