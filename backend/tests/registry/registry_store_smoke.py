"""Проверка хранилища реестра МСП на временной базе chDB."""

import asyncio
import sys
import tempfile
from datetime import date
from pathlib import Path

from chdb.session import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.repository.clickhouse.catalog.registry import ClickHouseMspRegistryRepository
from src.adapter.repository.clickhouse.engine.migrator import MIGRATION_DIR, Migrator
from src.models.company.registry import MspCompany
from tests.clickhouse.chdb_gateway import ChdbGateway

OLD = date(2026, 8, 10)
NEW = date(2026, 9, 10)


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="rlt-msp-store-") as temporary:
        session = Session(temporary)
        try:
            gateway = ChdbGateway(session)
            await Migrator(gateway, MIGRATION_DIR).apply_pending()
            # Пачка поиска в одну строку: проверяется разбиение длинного списка ИНН.
            store = ClickHouseMspRegistryRepository(gateway, lookup_batch=1)

            await store.save_many(
                [
                    MspCompany("7804428656", "Канцторг", OLD, "47.62"),
                    MspCompany("7707049388", "Выбыл из реестра", OLD, "46.76"),
                ]
            )
            await store.save_many(
                [
                    MspCompany(
                        "7804428656",
                        "Канцторг",
                        NEW,
                        "46.49.3",
                        "Торговля оптовая",
                        True,
                        ("47.62", "46.18"),
                        ("17.12.14",),
                        region="78",
                        region_name="Санкт-Петербург",
                    ),
                    MspCompany("636200108061", "ИП Иванов", NEW, "45.20"),
                ]
            )
            found = await store.find(["7804428656", "7707049388", "636200108061", "5003052454"])
            assert set(found) == {"7804428656", "7707049388", "636200108061"}, found
            shop = found["7804428656"]
            # Новая выгрузка заменяет сведения той же компании.
            assert shop.registry_date == NEW and shop.okved_main == "46.49.3", shop
            assert shop.okved_extra == ("47.62", "46.18"), shop
            assert shop.products == ("17.12.14",), shop
            assert shop.okved_main_reported, shop
            assert shop.region == "78" and shop.region_name == "Санкт-Петербург"
            assert not found["636200108061"].okved_main_reported

            await store.remove_older(NEW)
            found = await store.find(["7804428656", "7707049388", "636200108061"])
            assert set(found) == {"7804428656", "636200108061"}, found
            assert await store.find([]) == {}
        finally:
            session.close()
    print("Проверка хранилища реестра МСП пройдена")


if __name__ == "__main__":
    asyncio.run(main())
