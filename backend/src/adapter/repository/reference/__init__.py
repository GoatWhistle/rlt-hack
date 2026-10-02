"""Справочники из файлов: ОКПД2, рубрики, словарь, разделы каталогов, ОКЕИ, роли.

Это хранилище нормативных данных, поэтому оно и лежит в слое адаптеров: файлы
читаются здесь, а правила применения живут в сервисах. Справочники загружаются
двумя шагами, потому что ключ сравнения названий считает нормализатор: сначала
его правила и единицы, затем — таксономия, которой нужен готовый ключ.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.adapter.repository.reference.categories import FileSourceCategoryReference
from src.adapter.repository.reference.lexicon import FileLexicon
from src.adapter.repository.reference.loader import read_json
from src.adapter.repository.reference.okpd2 import FileOkpd2Reference
from src.adapter.repository.reference.okved_roles import FileOkvedRoles
from src.adapter.repository.reference.rubrics import FileRubricReference
from src.adapter.repository.reference.rules import FileTextRules
from src.adapter.repository.reference.units import FileUnitReference

REFERENCE_DIR = Path(__file__).resolve().parents[4] / "reference"


@dataclass(frozen=True, slots=True)
class NormalizerReference:
    rules: FileTextRules
    units: FileUnitReference


@dataclass(frozen=True, slots=True)
class ClassifierReference:
    okpd2: FileOkpd2Reference
    rubrics: FileRubricReference
    lexicon: FileLexicon
    categories: FileSourceCategoryReference


async def load_normalizer_reference(directory: Path = REFERENCE_DIR) -> NormalizerReference:
    return NormalizerReference(
        rules=FileTextRules.of(await read_json(directory / "text_rules.json")),
        units=FileUnitReference.of(await read_json(directory / "units.json")),
    )


async def load_classifier_reference(
    key: Callable[[str], str],
    word_stems: Callable[[str], tuple[str, ...]],
    directory: Path = REFERENCE_DIR,
) -> ClassifierReference:
    return ClassifierReference(
        okpd2=FileOkpd2Reference.of(await read_json(directory / "okpd2.json"), key),
        rubrics=FileRubricReference.of(await read_json(directory / "rubrics.json")),
        lexicon=FileLexicon.of(await read_json(directory / "lexicon.json"), word_stems),
        categories=FileSourceCategoryReference.of(
            await read_json(directory / "source_categories.json")
        ),
    )


async def load_category_names(directory: Path = REFERENCE_DIR) -> FileOkpd2Reference:
    """Названия ОКПД2 для показа: сравнение названий здесь не нужно."""
    return FileOkpd2Reference.of(await read_json(directory / "okpd2.json"), str.casefold)


async def load_okved_roles(directory: Path = REFERENCE_DIR) -> FileOkvedRoles:
    return FileOkvedRoles.of(await read_json(directory / "okved_roles.json"))


__all__ = [
    "REFERENCE_DIR",
    "ClassifierReference",
    "FileLexicon",
    "FileOkpd2Reference",
    "FileOkvedRoles",
    "FileRubricReference",
    "FileSourceCategoryReference",
    "FileTextRules",
    "FileUnitReference",
    "NormalizerReference",
    "load_category_names",
    "load_classifier_reference",
    "load_normalizer_reference",
    "load_okved_roles",
]
