"""Проверка сервиса синхронизации: источники обходятся одновременно.

ClickHouse и сеть не нужны: адаптеры, хранилище, нормализатор и классификатор
заменены заглушками. Проверяется, что все источники запускаются сразу, сбой
одного не отменяет результаты остальных, ограничение одновременных обходов
соблюдается, итоги попадают в журнал обхода, а собранный пакет перед записью
проходит нормализацию и только потом классификацию.
"""

import asyncio
import dataclasses
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.models.classification import Classification
from src.models.enums import FetchStatus, SourceType, SupplierRole
from src.models.journal import CrawlRun
from src.models.normalization import Normalization
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier
from src.service.supplier.worker import SupplierSyncWorker

PROVIDER_DELAY = 0.2


class FakeProvider:
    """Отдаёт готовый пакет через PROVIDER_DELAY или падает."""

    def __init__(
        self,
        name: str,
        suppliers: int = 1,
        failing: bool = False,
        offers: int = 0,
    ) -> None:
        self._source = Source(
            source_id=UUID(int=abs(hash(name)) % (2**128)),
            name=name,
            base_url=f"https://{name}.test/",
            source_type=SourceType.DIRECTORY,
            provider_name=name,
        )
        self._suppliers = suppliers
        self._offers = offers
        self._failing = failing
        self.started_at = 0.0

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        self.started_at = time.monotonic()
        await asyncio.sleep(PROVIDER_DELAY)
        if self._failing:
            raise RuntimeError("источник недоступен")
        suppliers = tuple(
            Supplier(supplier_id=UUID(int=index + 1), name=f"{self._source.name}-{index}")
            for index in range(self._suppliers)
        )
        moment = datetime.now(UTC)
        offers = tuple(
            Offer(
                offer_id=UUID(int=index + 100),
                source_id=self._source.source_id,
                external_id=str(index),
                url=f"{self._source.base_url}{index}",
                name=f"Отвертка {index}",
                first_seen_at=moment,
                last_seen_at=moment,
            )
            for index in range(self._offers)
        )
        return SupplierPackage(source=self._source, suppliers=suppliers, offers=offers)


class FakeStorage:
    def __init__(self, withdrawn: int = 0) -> None:
        self.packages: list[SupplierPackage] = []
        self._withdrawn = withdrawn

    async def save_package(self, package: SupplierPackage) -> int:
        self.packages.append(package)
        return self._withdrawn


class FakeJournal:
    def __init__(self, failing: bool = False) -> None:
        self.runs: list[CrawlRun] = []
        self._failing = failing

    async def save_run(self, run: CrawlRun) -> None:
        if self._failing:
            raise RuntimeError("журнал недоступен")
        self.runs.append(run)

    async def last_runs(self, source_id: UUID, limit: int = 10) -> list[CrawlRun]:
        return [run for run in self.runs if run.source_id == source_id][:limit]


class FakeClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeEnricher:
    """Проставляет компаниям роль и записывает порядок вызова."""

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def enrich(self, package: SupplierPackage) -> SupplierPackage:
        self._calls.append("enrich")
        suppliers = tuple(
            dataclasses.replace(supplier, role=SupplierRole.DISTRIBUTOR)
            for supplier in package.suppliers
        )
        return dataclasses.replace(package, suppliers=suppliers)


class FakeNormalizer:
    """Отмечает позиции нормализацией и записывает порядок вызова."""

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
    """Проставляет код только нормализованным позициям."""

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


def worker(
    providers,
    storage,
    journal,
    max_parallel: int = 4,
    calls: list[str] | None = None,
) -> SupplierSyncWorker:
    recorded = calls if calls is not None else []
    return SupplierSyncWorker(
        providers=providers,
        storage=storage,
        journal=journal,
        clock=FakeClock(),
        enricher=FakeEnricher(recorded),
        normalizer=FakeNormalizer(recorded),
        classifier=FakeClassifier(recorded),
        max_parallel_sources=max_parallel,
    )


async def check_concurrent_sources() -> None:
    providers = [FakeProvider(f"source{index}", suppliers=index + 1) for index in range(4)]
    storage = FakeStorage(withdrawn=2)
    journal = FakeJournal()
    started = time.monotonic()
    result = await worker(providers, storage, journal).run_once()
    elapsed = time.monotonic() - started

    assert len(result.sources) == 4, result
    assert all(item.status == FetchStatus.SUCCESS for item in result.sources), result
    assert result.suppliers_extracted == 1 + 2 + 3 + 4, result
    assert all(item.offers_withdrawn == 2 for item in result.sources), result
    assert len(storage.packages) == 4, storage.packages
    assert len(journal.runs) == 4, journal.runs
    # Четыре обхода по PROVIDER_DELAY прошли одновременно, а не по очереди.
    assert elapsed < PROVIDER_DELAY * 2, elapsed
    spread = max(p.started_at for p in providers) - min(p.started_at for p in providers)
    assert spread < PROVIDER_DELAY, spread


async def check_parallel_limit() -> None:
    providers = [FakeProvider(f"limited{index}") for index in range(4)]
    started = time.monotonic()
    await worker(providers, FakeStorage(), FakeJournal(), max_parallel=2).run_once()
    elapsed = time.monotonic() - started
    # Два одновременных обхода: четыре источника проходят в два приёма.
    assert elapsed >= PROVIDER_DELAY * 2, elapsed


async def check_failure_isolated() -> None:
    good = FakeProvider("good", suppliers=3)
    broken = FakeProvider("broken", failing=True)
    storage = FakeStorage()
    journal = FakeJournal()
    result = await worker([broken, good], storage, journal).run_once()

    statuses = {item.provider_name: item.status for item in result.sources}
    assert statuses == {"broken": FetchStatus.FAILED, "good": FetchStatus.SUCCESS}, statuses
    assert result.failed == 1, result
    # Данные исправного источника сохранены, несмотря на чужой сбой.
    assert [package.source.provider_name for package in storage.packages] == ["good"]
    failed_run = next(run for run in journal.runs if run.provider_name == "broken")
    assert failed_run.status == FetchStatus.FAILED
    assert "RuntimeError" in failed_run.error_message, failed_run.error_message
    assert failed_run.suppliers_extracted == 0


async def check_journal_failure_keeps_data() -> None:
    storage = FakeStorage()
    journal = FakeJournal(failing=True)
    result = await worker([FakeProvider("journalless")], storage, journal).run_once()
    # Журнал не влияет на собранные данные: обход остаётся успешным.
    assert result.sources[0].status == FetchStatus.SUCCESS, result
    assert len(storage.packages) == 1, storage.packages
    assert not journal.runs


async def check_enrichment_before_save() -> None:
    calls: list[str] = []
    storage = FakeStorage()
    provider = FakeProvider("enriched", suppliers=2, offers=2)
    await worker([provider], storage, FakeJournal(), calls=calls).run_once()

    # Обогащение идёт сразу после обхода, а классификатору нужно нормализованное
    # название, поэтому порядок обязателен.
    assert calls == ["enrich", "normalize", "classify"], calls
    assert all(s.role == SupplierRole.DISTRIBUTOR for s in storage.packages[0].suppliers)
    saved = storage.packages[0].offers
    assert len(saved) == 2, saved
    assert all(offer.normalization is not None for offer in saved), saved
    assert all(offer.classification.okpd2_code == "25.73" for offer in saved), saved


async def main() -> None:
    await check_enrichment_before_save()
    await check_concurrent_sources()
    await check_parallel_limit()
    await check_failure_isolated()
    await check_journal_failure_keeps_data()
    print("Проверка сервиса синхронизации пройдена")


if __name__ == "__main__":
    asyncio.run(main())
