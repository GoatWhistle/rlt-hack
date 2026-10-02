"""Проверка хранения производных значений на встроенном движке chDB.

Сервер ClickHouse и сеть не нужны. Проверяются применение миграции 0004,
запись и чтение нормализации с классификацией, пересчёт правил новой версией
строки, отчёт о покрытии и снятие с продажи после добавления колонок:
представление с `SELECT *` фиксирует список колонок при создании, поэтому
миграция обязана его пересоздать.
"""

import asyncio
import dataclasses
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from chdb.session import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.repository.clickhouse.catalog.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.engine.migrator import MIGRATION_DIR, Migrator
from src.adapter.repository.clickhouse.engine.versions import VersionSequencer
from src.models.catalog.classification import Classification
from src.models.catalog.normalization import Normalization
from src.models.catalog.offer import Offer
from src.models.enums import Availability, ClassificationMethod, ItemType
from tests.clickhouse.chdb_gateway import ChdbGateway

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
SOURCE = UUID(int=7)


def offer(index: int, **fields: object) -> Offer:
    return Offer(
        offer_id=UUID(int=index),
        source_id=SOURCE,
        external_id=str(index),
        url=f"https://example.test/{index}",
        name=f"Отвертка реверсивная {index}",
        first_seen_at=NOW,
        last_seen_at=NOW,
        brand="СИБРТЕХ",
        article=str(13000 + index),
        price=Decimal("525.00"),
        currency="RUR",
        **fields,
    )


def enriched(index: int, method: ClassificationMethod, code: str) -> Offer:
    return dataclasses.replace(
        offer(index),
        item_type=ItemType.GOODS,
        okpd2_code=code if method is ClassificationMethod.GOLD else "",
        normalization=Normalization(
            name=f"отвертка реверсивная {index}",
            key=f"сибртех {13000 + index}",
            brand="СИБРТЕХ",
            article=str(13000 + index),
            attributes={"length_mm": "150"},
            unit_code="796",
            unit_name="Штука",
            price_per_unit=Decimal("525.0000"),
            price_unit_code="796",
            currency="RUB",
            algorithm_version="normalizer-1",
        ),
        classification=Classification(
            okpd2_code=code,
            okpd2_level=len(code.replace(".", "")),
            rubric_code="tools",
            rubric_name="Инструмент и оснастка",
            item_type=ItemType.GOODS,
            method=method,
            confidence=0.6,
            evidence="словарь: отверт",
            algorithm_version="classifier-1",
        ),
    )


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="rlt-normalization-") as tmp:
        session = Session(tmp)
        try:
            gateway = ChdbGateway(session)
            applied = await Migrator(gateway, MIGRATION_DIR).apply_pending()
            assert "0004_normalization.sql" in applied, applied

            repository = ClickHouseOfferRepository(gateway, VersionSequencer())
            lexicon_offer = enriched(1, ClassificationMethod.LEXICON, "25.73")
            gold_offer = enriched(2, ClassificationMethod.GOLD, "17.12.14.129")
            await repository.save_many([lexicon_offer, gold_offer], NOW)

            stored = await repository.list_by_source(SOURCE, limit=10, offset=0)
            assert len(stored) == 2, stored
            first = next(item for item in stored if item.offer_id == UUID(int=1))
            assert first.name == lexicon_offer.name
            assert first.normalization.unit_code == "796", first.normalization
            assert first.normalization.unit_name == "Штука", first.normalization
            assert first.classification.rubric_name == "Инструмент и оснастка", first.classification
            assert first.normalization.price_per_unit == Decimal("525.0000"), first.normalization
            assert first.normalization.attributes == {"length_mm": "150"}, first.normalization
            assert first.classification.okpd2_code == "25.73", first.classification
            assert first.classification.method is ClassificationMethod.LEXICON
            assert first.classification.rubric_code == "tools", first.classification
            # Код, проставленный словарём, не выдаётся за код источника: иначе
            # при повторном разборе канал gold закрыл бы его навсегда.
            assert first.okpd2_code == "", first

            second = next(item for item in stored if item.offer_id == UUID(int=2))
            assert second.okpd2_code == "17.12.14.129", second
            assert second.classification.method is ClassificationMethod.GOLD

            # Каноническое представление: у каждого смысла ровно одно поле.
            canonical = await gateway.select(
                "SELECT name, rubric, rubric_name, unit_code, unit_name, method, currency "
                "FROM supplier_search.offers_normalized ORDER BY offer_id"
            )
            assert len(canonical) == 2, canonical
            assert canonical[0][0] == "отвертка реверсивная 1", canonical[0]
            assert canonical[0][1] == "tools", canonical[0]
            assert canonical[0][2] == "Инструмент и оснастка", canonical[0]
            assert canonical[0][3] == "796", canonical[0]
            assert canonical[0][4] == "Штука", canonical[0]
            assert canonical[0][5] == "lexicon", canonical[0]
            # Валюта сведена к ISO: источник отдал RUR.
            assert canonical[0][6] == "RUB", canonical[0]

            report = await repository.coverage()
            assert report.offers == 2, report
            assert report.normalized == 2, report
            assert report.classified == 2, report
            assert report.with_price_per_unit == 2, report
            methods = {share.name: share.offers for share in report.by_method}
            assert methods == {"lexicon": 1, "gold": 1}, methods
            rubrics = {share.name: share.offers for share in report.by_rubric}
            assert rubrics == {"tools": 2}, rubrics

            # Пересчёт новыми правилами: строка перезаписывается новой версией.
            recomputed = dataclasses.replace(
                first,
                classification=dataclasses.replace(
                    first.classification,
                    okpd2_code="25.73.30",
                    algorithm_version="classifier-2",
                ),
            )
            await repository.save_many([recomputed], NOW)
            again = await repository.list_by_source(SOURCE, limit=10, offset=0)
            updated = next(item for item in again if item.offer_id == UUID(int=1))
            assert updated.classification.okpd2_code == "25.73.30", updated.classification
            assert updated.classification.algorithm_version == "classifier-2", updated
            assert len(again) == 2, again

            # Снятие с продажи читает представление: после ALTER оно пересоздано,
            # иначе SELECT * вернул бы меньше колонок, чем ждёт таблица.
            later = datetime(2026, 10, 2, 12, tzinfo=UTC)
            withdrawn = await repository.withdraw_absent(SOURCE, later)
            assert withdrawn == 2, withdrawn
            after = await repository.list_by_source(SOURCE, limit=10, offset=0)
            assert all(item.availability is Availability.UNAVAILABLE for item in after), after
            # Производные значения переживают снятие: строка пишется целиком.
            assert all(item.normalization.unit_code == "796" for item in after), after
        finally:
            session.close()
    print("Проверка хранения нормализации пройдена")


if __name__ == "__main__":
    asyncio.run(main())
