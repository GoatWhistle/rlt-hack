"""Состав текста вектора: поля позиции, компания и её местоположение.

Проверяется и то, что хеш свежести считается по этому же составу: правка
региона компании обязана пересчитать вектор, хотя поля предложения не менялись.
"""

import asyncio
import sys
import tempfile
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from chdb.session import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.repository.clickhouse.embedding import ClickHouseEmbeddingRepository
from src.adapter.repository.clickhouse.migrator import Migrator
from src.adapter.repository.clickhouse.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.classification import Classification
from src.models.embedding import EmbeddingDocument
from src.models.enums import ClassificationMethod, ItemType, SupplierRole, VerificationStatus
from src.models.normalization import Normalization
from src.models.offer import Offer
from src.models.supplier import Supplier
from src.service.embedding.worker import document_text
from tests.clickhouse.chdb_gateway import ChdbGateway

MODEL = "test:4b"


def test_text() -> None:
    document = EmbeddingDocument(
        offer_id=uuid4(),
        content_hash="hash",
        name="Бумага А4 Снегурочка 500 л.",
        normalized_name="бумага офисная",
        brand="Снегурочка",
        article="SN-500",
        item_type="goods",
        unit="пачка",
        source_category="Канцелярия / Бумага",
        okpd2_code="17.12.14.110",
        rubric_name="Бумага и картон",
        supplier_role="manufacturer",
        supplier_name='ООО "Ромашка"',
        region="Московская область",
        address="г. Подольск, ул. Заводская, 1",
        description="Офисная бумага плотностью 80 г/м2.",
        attributes={"плотность": "80 г/м2", "формат": "A4"},
    )
    text = document_text(document)
    # Местоположение поставщика попадает в вектор: регион и адрес вместе.
    assert "Местоположение: Московская область, г. Подольск, ул. Заводская, 1" in text
    for expected in (
        "Бумага А4 Снегурочка 500 л.",
        "Предмет: бумага офисная",
        "Тип: товар",
        "Бренд: Снегурочка",
        "Артикул: SN-500",
        "Характеристики: плотность: 80 г/м2; формат: A4",
        "Единица: пачка",
        "Раздел каталога: Канцелярия / Бумага",
        "ОКПД2: 17.12.14.110",
        "Рубрика: Бумага и картон",
        'Поставщик: ООО "Ромашка"',
        "Роль: производитель",
        "Офисная бумага плотностью 80 г/м2.",
    ):
        assert expected in text, expected

    # Пустые поля не оставляют подписей без значения.
    sparse = document_text(EmbeddingDocument(uuid4(), "hash", "Станок"))
    assert sparse == "Станок", sparse

    # Ядро названия не дублируется, когда совпадает с названием.
    same = document_text(EmbeddingDocument(uuid4(), "hash", "Станок", normalized_name="Станок"))
    assert same == "Станок", same

    # Неизвестный код роли подписи не создаёт, неизвестный тип остаётся как есть.
    other = document_text(EmbeddingDocument(uuid4(), "hash", "Станок", item_type="unknown"))
    assert "Роль:" not in other and "Тип: unknown" in other, other


async def check_freshness() -> None:
    with tempfile.TemporaryDirectory(prefix="rlt-embedding-doc-") as directory:
        session = cast("Callable[[str], Any]", Session)(str(Path(directory) / "db"))
        try:
            gateway = ChdbGateway(session)
            await Migrator(gateway).apply_pending()
            versions = VersionSequencer()
            offers = ClickHouseOfferRepository(gateway, versions)
            suppliers = ClickHouseSupplierRepository(gateway, versions)
            repository = ClickHouseEmbeddingRepository(gateway, versions)
            now = datetime.now(UTC)
            supplier = Supplier(
                supplier_id=uuid4(),
                name='ООО "Ромашка"',
                inn="7707083893",
                region="Москва",
                contacts={"address": "г. Москва, ул. Тверская, 1"},
            )
            offer = Offer(
                uuid4(),
                uuid4(),
                "1",
                "https://example.test/1",
                "бумага",
                now,
                now,
                supplier_id=supplier.supplier_id,
                seller_status=VerificationStatus.UNVERIFIED,
                item_type=ItemType.GOODS,
                unit="пачка",
                source_category="Канцелярия",
                supplier_role=SupplierRole.MANUFACTURER,
                content_hash="paper-v1",
                normalization=Normalization(name="бумага офисная", unit_name="пачка"),
                classification=Classification(
                    okpd2_code="17.12.14.110",
                    rubric_name="Бумага и картон",
                    method=ClassificationMethod.REFERENCE,
                ),
            )
            await suppliers.save_many([supplier])
            await offers.save_many([offer], now)

            pending = await repository.pending(MODEL, 2, 10)
            assert len(pending) == 1, pending
            document = pending[0]
            # Компания и её место читаются вместе с позицией.
            assert document.supplier_name == 'ООО "Ромашка"'
            assert document.region == "Москва"
            assert document.address == "г. Москва, ул. Тверская, 1"
            assert document.normalized_name == "бумага офисная"
            assert document.rubric_name == "Бумага и картон"
            assert document.okpd2_code == "17.12.14.110"
            assert document.source_category == "Канцелярия"
            assert document.item_type == "goods" and document.supplier_role == "manufacturer"

            await repository.save([document], [[1.0, 0.0]], MODEL)
            assert await repository.pending(MODEL, 2, 10) == [], "Свежий вектор не пересчитывается"

            # Переезд компании меняет текст вектора, хотя позиция та же.
            moved = Supplier(
                supplier_id=supplier.supplier_id,
                name=supplier.name,
                inn=supplier.inn,
                region="Санкт-Петербург",
                contacts={"address": "г. Санкт-Петербург, Невский пр., 1"},
            )
            await suppliers.save_many([moved])
            stale = await repository.pending(MODEL, 2, 10)
            assert len(stale) == 1, "Смена региона компании обязана пересчитать вектор"
            assert stale[0].region == "Санкт-Петербург"
            assert stale[0].content_hash != document.content_hash
            await repository.save([stale[0]], [[0.0, 1.0]], MODEL)
            assert await repository.pending(MODEL, 2, 10) == []

            # Порядок характеристик в Map хеш не меняет: смысл позиции тот же.
            attributed = replace(offer, attributes={"формат": "A4", "плотность": "80"})
            await offers.save_many([attributed], now)
            reordered = await repository.pending(MODEL, 2, 10)
            assert len(reordered) == 1, "Новые характеристики пересчитывают вектор"
            await repository.save([reordered[0]], [[1.0, 0.0]], MODEL)
            await offers.save_many(
                [replace(attributed, attributes={"плотность": "80", "формат": "A4"})], now
            )
            assert await repository.pending(MODEL, 2, 10) == [], "Порядок ключей хеш не меняет"
        finally:
            session.cleanup()


if __name__ == "__main__":
    test_text()
    asyncio.run(check_freshness())
    print("Текст и свежесть вектора: проверки прошли")
