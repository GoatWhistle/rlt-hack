"""Классификатор позиций: код ОКПД2, рубрика и тип с указанием канала.

Сервис вызывается через интерфейс после нормализации и до записи в хранилище:
он работает с нормализованным названием, поэтому порядок обязателен. Каналы
перебираются от самого надёжного к запасному, и первый сработавший выигрывает.
Если не сработал ни один — позиция остаётся без кода, и это видно в отчёте.
"""

import asyncio
import dataclasses
import logging
from collections.abc import Callable, Mapping, Sequence

from src.models.catalog.classification import Classification
from src.models.catalog.offer import Offer
from src.models.catalog.package import SupplierPackage
from src.models.enums import ClassificationMethod, ItemType
from src.service.classifier import channels
from src.service.classifier.archive import build_index
from src.service.classifier.protocols import (
    ArchiveCatalog,
    LexiconReference,
    Okpd2Reference,
    RubricReference,
    SourceCategoryReference,
)
from src.service.classifier.taxonomy import (
    item_type_by_phrase,
    item_type_of,
    level_of,
    rubric_of,
)
from src.service.normalizer.text import clean, stems

logger = logging.getLogger(__name__)

VERSION = "classifier-1"
ARCHIVE_LIMIT = 500_000


def _has_code(offer: Offer) -> bool:
    return bool(offer.classification and offer.classification.okpd2_code)


class OfferClassifier:
    """Проставляет код, рубрику и тип позиции по детерминированным каналам."""

    def __init__(
        self,
        okpd2: Okpd2Reference,
        rubrics: RubricReference,
        lexicon: LexiconReference,
        categories: SourceCategoryReference,
        archive: ArchiveCatalog | None = None,
        archive_limit: int = ARCHIVE_LIMIT,
        head_window: int = channels.HEAD_WINDOW,
        name_key: Callable[[str], str] | None = None,
        version: str = VERSION,
    ) -> None:
        self._okpd2 = okpd2
        self._rubrics = rubrics
        self._lexicon = lexicon
        self._categories = categories
        self._archive = archive
        self._archive_limit = archive_limit
        self._head_window = head_window
        self._name_key = name_key or (lambda value: clean(value).lower())
        self._version = version
        self._index: dict[str, str] | None = None

    @property
    def version(self) -> str:
        return self._version

    async def classify(self, package: SupplierPackage) -> SupplierPackage:
        if not package.offers:
            return package
        index = await self._archive_index()
        classified = await asyncio.to_thread(
            self._classify_all, package.offers, package.source.provider_name, index
        )
        logger.info(
            "Классификация %s: позиций — %d, с кодом — %d",
            package.source.provider_name,
            len(classified),
            sum(1 for offer in classified if _has_code(offer)),
        )
        return dataclasses.replace(package, offers=tuple(classified))

    def classify_offer(
        self,
        offer: Offer,
        provider_name: str,
        index: Mapping[str, str],
    ) -> Offer:
        name = offer.normalization.name if offer.normalization else offer.name
        key = self._name_key(name)
        hit = (
            channels.gold(offer.okpd2_code, provider_name)
            or channels.by_reference(key, name, self._okpd2)
            or channels.by_archive(key, name, index)
            or channels.by_source_category(provider_name, offer.source_category, self._categories)
            or channels.by_lexicon(stems(name), self._lexicon, self._head_window)
        )
        classification = self._describe(hit, offer.name)
        return dataclasses.replace(
            offer,
            classification=classification,
            okpd2_code=offer.okpd2_code or classification.okpd2_code,
            item_type=(
                classification.item_type
                if classification.item_type is not ItemType.UNKNOWN
                else offer.item_type
            ),
        )

    def _describe(self, hit: channels.Hit | None, raw_name: str) -> Classification:
        code = hit.code if hit else ""
        rubric = rubric_of(code, self._rubrics.prefixes) if code else ""
        item_type = item_type_of(code, self._rubrics.class_types)
        evidence = hit.evidence if hit else ""
        if item_type is ItemType.UNKNOWN:
            item_type, phrase = item_type_by_phrase(raw_name, self._rubrics.type_phrases)
            if phrase:
                found = f"оборот названия: {phrase}"
                evidence = f"{evidence}; {found}" if evidence else found
        return Classification(
            okpd2_code=code,
            okpd2_name=self._okpd2.name_of(code) if code else "",
            okpd2_level=level_of(code) if code else 0,
            rubric_code=rubric,
            rubric_name=self._rubrics.names.get(rubric, ""),
            item_type=item_type,
            method=hit.method if hit else ClassificationMethod.NONE,
            confidence=hit.confidence if hit else 0.0,
            evidence=evidence,
            algorithm_version=self._version,
        )

    async def _archive_index(self) -> Mapping[str, str]:
        """Индекс архива строится один раз на запуск сервиса."""
        if self._index is not None:
            return self._index
        if self._archive is None:
            self._index = {}
            return self._index
        items = await self._archive.load_items(self._archive_limit)
        self._index = build_index(items, self._name_key)
        logger.info("Индекс архива закупок: названий — %d", len(self._index))
        return self._index

    def _classify_all(
        self,
        offers: Sequence[Offer],
        provider_name: str,
        index: Mapping[str, str],
    ) -> list[Offer]:
        return [self.classify_offer(offer, provider_name, index) for offer in offers]
