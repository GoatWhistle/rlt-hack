"""Нормализатор позиций: единая форма записи для всех источников.

Сервис вызывается через интерфейс сразу после обхода источника и до записи в
хранилище. Он ничего не знает ни о ClickHouse, ни о парсерах: на вход пакет
источника, на выход тот же пакет с заполненной нормализацией. Разбор —
вычислительная работа без ввода-вывода, поэтому для пакета целиком он уходит в
пул потоков и не держит событийный цикл.
"""

import asyncio
import dataclasses
import logging
from collections.abc import Sequence

from src.models.normalization import Normalization
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.service.normalizer import attributes as attribute_rules
from src.service.normalizer import names, units
from src.service.normalizer.protocols import TextRules, UnitReference
from src.service.normalizer.text import clean, stems

logger = logging.getLogger(__name__)

VERSION = "normalizer-1"
MAX_KEY_LENGTH = 160


class OfferNormalizer:
    """Приводит названия, характеристики, единицы и цены к одному виду."""

    def __init__(
        self,
        units_reference: UnitReference,
        rules: TextRules,
        version: str = VERSION,
    ) -> None:
        self._units = units_reference
        self._rules = rules
        self._version = version

    @property
    def version(self) -> str:
        return self._version

    async def normalize(self, package: SupplierPackage) -> SupplierPackage:
        if not package.offers:
            return package
        normalized = await asyncio.to_thread(self._normalize_all, package.offers)
        logger.info(
            "Нормализация %s: позиций — %d",
            package.source.provider_name,
            len(normalized),
        )
        return dataclasses.replace(package, offers=tuple(normalized))

    def normalize_offer(self, offer: Offer) -> Offer:
        """Одна позиция: исходные поля сохраняются, результат кладётся рядом."""
        parts = names.decompose(offer.name, self._rules, offer.brand, offer.article)
        source_attributes = attribute_rules.canonical(offer.attributes, self._rules)
        merged = attribute_rules.merge(parts.attributes, source_attributes)
        unit = units.resolve(offer.unit, merged, self._units)
        unit_price = units.price_per_unit(offer.price, unit, merged, self._units)
        normalization = Normalization(
            name=parts.core,
            key=self.fingerprint(parts),
            brand=parts.brand,
            article=parts.article,
            attributes=merged,
            unit_code=unit.code if unit else "",
            unit_name=unit.name if unit else "",
            price_per_unit=unit_price.price,
            price_unit_code=unit_price.unit_code,
            currency=units.currency(offer.currency, self._rules.currencies),
            algorithm_version=self._version,
        )
        return dataclasses.replace(offer, normalization=normalization)

    def core_name(self, name: str) -> str:
        """Ядро названия без хранения результата: нужно и классификатору."""
        return names.decompose(name, self._rules).core

    def name_key(self, text: str) -> str:
        """Ключ сравнения названий: основы слов ядра через пробел.

        Им пользуются справочник ОКПД2 и индекс архива, поэтому обе стороны
        сравнения строятся одной функцией и расходиться не могут.
        """
        return " ".join(self.name_stems(text))

    def name_stems(self, text: str) -> tuple[str, ...]:
        return stems(self.core_name(text))

    def fingerprint(self, parts: names.NameParts) -> str:
        """Ключ склейки: бренд с артикулом надёжнее названия."""
        if parts.brand and parts.article:
            return clean(f"{parts.brand} {parts.article}").lower()[:MAX_KEY_LENGTH]
        return parts.core[:MAX_KEY_LENGTH]

    def _normalize_all(self, offers: Sequence[Offer]) -> list[Offer]:
        return [self.normalize_offer(offer) for offer in offers]
