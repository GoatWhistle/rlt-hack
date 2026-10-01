"""Проверка пересчёта производных значений у сохранённых позиций.

ClickHouse не нужен: каталог позиций заменён заглушкой со страницами. Проверяются
обход источников по страницам, передача пакета сначала нормализатору и только
потом классификатору, ограничение по числу позиций и сохранение результата.
"""

import asyncio
import dataclasses
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.models.classification import Classification
from src.models.coverage import CoverageReport
from src.models.enums import SourceType
from src.models.normalization import Normalization
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.service.supplier.enrich import OfferEnrichmentService

NOW = datetime(2026, 10, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeSources:
    def __init__(self, *names: str) -> None:
        self._sources = [
            Source(
                source_id=UUID(int=index + 1),
                name=name,
                base_url=f"https://{name}.test/",
                source_type=SourceType.FEED,
                provider_name=name,
            )
            for index, name in enumerate(names)
        ]

    async def list_all(self) -> list[Source]:
        return list(self._sources)


class FakeOfferCatalog:
    def __init__(self, offers: dict[UUID, list[Offer]]) -> None:
        self._offers = offers
        self.saved: list[Offer] = []
        self.pages = 0

    async def list_by_source(self, source_id: UUID, limit: int, offset: int) -> list[Offer]:
        self.pages += 1
        return self._offers.get(source_id, [])[offset : offset + limit]

    async def save_many(self, offers, updated_at: datetime) -> None:
        assert updated_at == NOW, updated_at
        self.saved.extend(offers)

    async def coverage(self) -> CoverageReport:
        return CoverageReport(offers=len(self.saved))


class FakeNormalizer:
    version = "normalizer-test"

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def normalize(self, package: SupplierPackage) -> SupplierPackage:
        self._calls.append("normalize")
        offers = tuple(
            dataclasses.replace(offer, normalization=Normalization(name=offer.name.lower()))
            for offer in package.offers
        )
        return dataclasses.replace(package, offers=offers)


class FakeClassifier:
    version = "classifier-test"

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def classify(self, package: SupplierPackage) -> SupplierPackage:
        self._calls.append("classify")
        offers = tuple(
            dataclasses.replace(
                offer,
                classification=Classification(okpd2_code="25.73" if offer.normalization else ""),
            )
            for offer in package.offers
        )
        return dataclasses.replace(package, offers=offers)


def offers(source_id: UUID, count: int) -> list[Offer]:
    return [
        Offer(
            offer_id=UUID(int=1000 + index),
            source_id=source_id,
            external_id=str(index),
            url=f"https://example.test/{index}",
            name=f"Отвертка {index}",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
        for index in range(count)
    ]


def service(catalog: FakeOfferCatalog, sources: FakeSources, calls: list[str], batch: int = 2):
    return OfferEnrichmentService(
        sources=sources,
        offers=catalog,
        normalizer=FakeNormalizer(calls),
        classifier=FakeClassifier(calls),
        clock=FakeClock(),
        batch_size=batch,
    )


async def check_all_sources_processed() -> None:
    sources = FakeSources("feed", "site")
    catalog = FakeOfferCatalog(
        {UUID(int=1): offers(UUID(int=1), 5), UUID(int=2): offers(UUID(int=2), 1)}
    )
    calls: list[str] = []
    result = await service(catalog, sources, calls).run()

    assert result.offers == 6, result
    assert result.classified == 6, result
    assert result.sources == 2, result
    assert result.normalizer_version == "normalizer-test", result
    assert len(catalog.saved) == 6, catalog.saved
    # Порядок шагов тот же, что и при обходе источника.
    assert calls[:2] == ["normalize", "classify"], calls
    assert calls.count("normalize") == calls.count("classify"), calls
    assert all(offer.classification.okpd2_code == "25.73" for offer in catalog.saved)


async def check_limit_stops_early() -> None:
    sources = FakeSources("feed")
    catalog = FakeOfferCatalog({UUID(int=1): offers(UUID(int=1), 10)})
    result = await service(catalog, sources, []).run(limit=3)
    # Последняя пачка укорачивается до остатка лимита: лишнего не читается.
    assert result.offers == 3, result
    assert len(catalog.saved) == 3, catalog.saved


async def check_empty_source() -> None:
    sources = FakeSources("empty")
    catalog = FakeOfferCatalog({})
    result = await service(catalog, sources, []).run()
    assert result.offers == 0, result
    assert result.sources == 0, result
    assert catalog.saved == []


async def main() -> None:
    await check_all_sources_processed()
    await check_limit_stops_early()
    await check_empty_source()
    print("Проверка пересчёта позиций пройдена")


if __name__ == "__main__":
    asyncio.run(main())
