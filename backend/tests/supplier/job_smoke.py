"""Проверка джобы сбора на временной базе chDB.

Покрыты: применение миграций, сохранение пакета источника, время первой
встречи, снятие с продажи исчезнувших предложений, отсутствие снятия при пустом
пакете, импорт компаний из датасета, роль компании по реестру МСП и журнал
обхода. Нормализатор и
классификатор подключены настоящие, со справочниками репозитория: проверяется
вся цепочка от разбора фида до производных колонок в хранилище. Сеть не
используется: HTTP-клиент адаптера работает через httpx.MockTransport.
"""

import asyncio
import sys
import tempfile
from datetime import date
from pathlib import Path

import httpx
from chdb.session import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.repository.clickhouse.journal import ClickHouseJournalRepository
from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR, Migrator
from src.adapter.repository.clickhouse.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.package import ClickHousePackageRepository
from src.adapter.repository.clickhouse.registry import ClickHouseMspRegistryRepository
from src.adapter.repository.clickhouse.source import ClickHouseSourceRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.adapter.repository.reference import (
    load_classifier_reference,
    load_normalizer_reference,
    load_okved_roles,
)
from src.adapter.supplier import identity
from src.adapter.supplier.supplier_dataset import SupplierDatasetProvider
from src.adapter.supplier.yml_feed import YmlFeedProvider
from src.adapter.system.clock import SystemClock
from src.models.enums import (
    ClassificationMethod,
    FetchStatus,
    SourceType,
    SupplierRole,
    VerificationStatus,
)
from src.models.registry import MspCompany
from src.models.source import Source
from src.service.classifier import OfferClassifier
from src.service.normalizer import OfferNormalizer
from src.service.registry import SupplierRegistryEnricher
from src.service.supplier.worker import SupplierSyncWorker
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.supplier.fixtures import FEED_EMPTY, FEED_FULL, FEED_WITHOUT_A3, SUPPLIERS_CSV

SHOP_INN = "7804428656"
FEED_URL = "https://shop.test/feed.xml"


def feed_transport(body: str) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == FEED_URL, request.url
        return httpx.Response(200, text=body, headers={"Content-Type": "application/xml"})

    return httpx.MockTransport(handler)


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="rlt-job-") as temporary:
        root = Path(temporary)
        session = Session(str(root / "db"))
        try:
            gateway = ChdbGateway(session)
            applied = await Migrator(gateway, MIGRATION_DIR).apply_pending()
            assert applied, "миграции не применились"
            assert not await Migrator(gateway, MIGRATION_DIR).apply_pending(), "повтор миграций"

            normalizer_reference = await load_normalizer_reference()
            normalizer = OfferNormalizer(normalizer_reference.units, normalizer_reference.rules)
            classifier_reference = await load_classifier_reference(
                normalizer.name_key, normalizer.name_stems
            )
            classifier = OfferClassifier(
                okpd2=classifier_reference.okpd2,
                rubrics=classifier_reference.rubrics,
                lexicon=classifier_reference.lexicon,
                categories=classifier_reference.categories,
                name_key=normalizer.name_key,
            )

            registry = ClickHouseMspRegistryRepository(gateway)
            await registry.save_many(
                [
                    MspCompany(
                        inn=SHOP_INN,
                        name="ООО «КАНЦТОРГ»",
                        registry_date=date(2026, 9, 10),
                        okved_main="46.49.3",
                        okved_main_name="Торговля оптовая канцелярскими товарами",
                        okved_extra=("47.62",),
                    )
                ]
            )
            enricher = SupplierRegistryEnricher(registry, await load_okved_roles())

            versions = VersionSequencer()
            sources = ClickHouseSourceRepository(gateway, versions)
            offers = ClickHouseOfferRepository(gateway, versions)
            journal = ClickHouseJournalRepository(gateway)
            storage = ClickHousePackageRepository(
                sources=sources,
                suppliers=ClickHouseSupplierRepository(gateway, versions),
                offers=offers,
                batch_size=100,
            )

            feed_source = Source(
                source_id=identity.source_id("https://shop.test/", "yml_feed"),
                name="Канцторг",
                base_url="https://shop.test/",
                source_type=SourceType.FEED,
                provider_name="yml_feed",
                ownership_status=VerificationStatus.VERIFIED,
                ownership_evidence_url="https://shop.test/about",
            )
            dataset_path = root / "Поставщики_24-25.csv"
            dataset_path.write_text(SUPPLIERS_CSV, encoding="utf-8")
            dataset_source = Source(
                source_id=identity.source_id(dataset_path.as_uri(), "supplier_dataset"),
                name="Поставщики из задания",
                base_url=dataset_path.as_uri(),
                source_type=SourceType.DATASET,
                provider_name="supplier_dataset",
            )

            async def sync(feed_body: str):
                worker = SupplierSyncWorker(
                    providers=[
                        YmlFeedProvider(
                            feed_source,
                            feed_url=FEED_URL,
                            supplier_inn=SHOP_INN,
                            transport=feed_transport(feed_body),
                        ),
                        SupplierDatasetProvider(
                            dataset_source, dataset_path, region="Санкт-Петербург"
                        ),
                    ],
                    storage=storage,
                    journal=journal,
                    clock=SystemClock(),
                    enricher=enricher,
                    normalizer=normalizer,
                    classifier=classifier,
                    max_parallel_sources=2,
                )
                result = await worker.run_once()
                assert result.failed == 0, result
                return {item.provider_name: item for item in result.sources}

            async def rows(sql: str) -> list[tuple]:
                return await gateway.select(sql)

            # Первый обход: источники, компании и предложения записаны.
            first = await sync(FEED_FULL)
            assert first["yml_feed"].offers_extracted == 2, first
            assert first["yml_feed"].offers_withdrawn == 0, first
            assert first["supplier_dataset"].suppliers_extracted == 3, first

            # Роль по ОКВЭД пришла из реестра; компания вне реестра осталась без неё.
            roles = await rows(
                "SELECT inn, role, role_evidence, okved_codes "
                "FROM supplier_search.suppliers_current ORDER BY inn"
            )
            by_inn = {row[0]: row[1:] for row in roles}
            assert by_inn[SHOP_INN][0] == str(SupplierRole.DISTRIBUTOR), roles
            assert "46.49.3" in by_inn[SHOP_INN][1], roles
            assert list(by_inn[SHOP_INN][2]) == ["46.49.3", "47.62"], roles
            assert by_inn["7707049388"][0] == str(SupplierRole.UNKNOWN), roles

            stored_sources = await sources.list_all()
            assert {source.provider_name for source in stored_sources} == {
                "yml_feed",
                "supplier_dataset",
            }, stored_sources
            assert (await rows("SELECT count() FROM supplier_search.suppliers_current"))[0][
                0
            ] == 3, "компании датасета и владелец фида свёрнуты по ИНН"
            offer_rows = await rows(
                "SELECT external_id, name, price, availability, first_seen_at "
                "FROM supplier_search.offers_current ORDER BY external_id"
            )
            assert [row[0] for row in offer_rows] == ["A-1", "A-2"], offer_rows
            first_seen = {row[0]: row[4] for row in offer_rows}
            assert float(offer_rows[0][2]) == 350.50, offer_rows

            # Производные значения записаны тем же обходом, что и исходные поля.
            derived = await rows(
                "SELECT external_id, normalized_name, normalizer_version, okpd2_code, rubric, "
                "classification_method, classifier_version, unit_code, price_per_unit "
                "FROM supplier_search.offers_current ORDER BY external_id"
            )
            assert all(row[1] for row in derived), derived
            assert all(row[2] == normalizer.version for row in derived), derived
            assert all(row[6] == classifier.version for row in derived), derived
            classified = [row for row in derived if row[3]]
            assert classified, derived
            assert all(row[4] for row in classified), classified
            assert all(row[5] != str(ClassificationMethod.NONE) for row in classified), classified

            coverage = await offers.coverage()
            assert coverage.offers == 2, coverage
            assert coverage.normalized == 2, coverage
            assert coverage.classified >= 1, coverage

            # Второй обход: А3 исчезла из фида, у А4 изменилась только цена.
            second = await sync(FEED_WITHOUT_A3)
            assert second["yml_feed"].offers_extracted == 1, second
            assert second["yml_feed"].offers_withdrawn == 1, second
            after = await rows(
                "SELECT external_id, price, availability, first_seen_at "
                "FROM supplier_search.offers_current ORDER BY external_id"
            )
            assert [row[0] for row in after] == ["A-1", "A-2"], after
            assert float(after[0][1]) == 399.00, after
            assert after[0][2] == "available", after
            # Снятая позиция сохранена со статусом недоступности, а не удалена.
            assert after[1][2] == "unavailable", after
            # Время первой встречи не теряется при новой версии строки.
            assert after[0][3] == first_seen["A-1"], (after, first_seen)

            # Третий обход: фид пуст, снимать предложения по нему нельзя.
            third = await sync(FEED_EMPTY)
            assert third["yml_feed"].offers_extracted == 0, third
            assert third["yml_feed"].offers_withdrawn == 0, third
            remaining = await rows(
                "SELECT availability FROM supplier_search.offers_current WHERE external_id = 'A-1'"
            )
            assert remaining[0][0] == "available", remaining

            # Журнал обхода: по записи на каждый обход источника.
            runs = await journal.last_runs(feed_source.source_id, limit=10)
            assert len(runs) == 3, runs
            assert all(run.status == FetchStatus.SUCCESS for run in runs), runs
            assert runs[0].provider_name == "yml_feed", runs[0]
            assert [run.offers_extracted for run in runs] == [0, 1, 2], runs
            dataset_runs = await journal.last_runs(dataset_source.source_id)
            assert len(dataset_runs) == 3, dataset_runs
            assert all(run.suppliers_extracted == 3 for run in dataset_runs), dataset_runs
        finally:
            session.close()
    print("Проверка джобы сбора пройдена")


if __name__ == "__main__":
    asyncio.run(main())
