"""Проверка перевода сохранённых позиций на действующее правило ключа.

ClickHouse не нужен: каталог позиций заменён заглушкой. Проверяются сохранение
времени первой встречи, слияние позиций, которые стали одной, снятие старых
строк по отметке перезаписи и повторный запуск, который ничего не меняет.
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.supplier import identity
from src.adapter.supplier.offer_identity import OfferIdentityRules
from src.models.coverage import CoverageReport
from src.models.enums import SourceType
from src.models.offer import Offer
from src.models.source import Source
from src.service.supplier.reidentify import OfferReidentifyService

EARLY = datetime(2026, 9, 1, tzinfo=UTC)
LATE = datetime(2026, 9, 20, tzinfo=UTC)
NOW = datetime(2026, 10, 1, tzinfo=UTC)
SOURCE_ID = UUID(int=1)
PAGE = "https://texzakaz.ru/p/252"


class FakeClock:
    def __init__(self) -> None:
        self.moment = NOW

    def now(self) -> datetime:
        self.moment += timedelta(seconds=1)
        return self.moment


class FakeSources:
    async def list_all(self) -> list[Source]:
        return [
            Source(
                source_id=SOURCE_ID,
                name="ТехЗаказ",
                base_url="https://texzakaz.ru/",
                source_type=SourceType.DIRECTORY,
                provider_name="texzakaz_web",
            )
        ]


class FakeOfferCatalog:
    """Хранит позиции и повторяет отбор устаревших по отметке перезаписи."""

    def __init__(self, offers: list[Offer]) -> None:
        self.rows: dict[UUID, tuple[Offer, datetime]] = {
            offer.offer_id: (offer, EARLY) for offer in offers
        }

    async def list_by_source(self, source_id: UUID, limit: int, offset: int) -> list[Offer]:
        rows = [offer for offer, _ in self.rows.values() if offer.source_id == source_id]
        rows.sort(key=lambda offer: str(offer.offer_id))
        return rows[offset : offset + limit]

    async def save_many(self, offers, updated_at: datetime) -> None:
        for offer in offers:
            self.rows[offer.offer_id] = (offer, updated_at)

    async def delete_stale(self, source_id: UUID, written_at: datetime) -> int:
        stale = [
            offer_id
            for offer_id, (offer, updated_at) in self.rows.items()
            if offer.source_id == source_id and updated_at < written_at
        ]
        for offer_id in stale:
            del self.rows[offer_id]
        return len(stale)

    async def coverage(self) -> CoverageReport:
        return CoverageReport(offers=len(self.rows))


def legacy_offer(name: str, first_seen: datetime) -> Offer:
    """Позиция со старым ключом: адрес плюс само название."""
    external_id = f"{PAGE}#{name}"
    return Offer(
        offer_id=identity.offer_id(SOURCE_ID, external_id),
        source_id=SOURCE_ID,
        external_id=external_id,
        url=PAGE,
        name=name,
        first_seen_at=first_seen,
        last_seen_at=LATE,
    )


def service(catalog: FakeOfferCatalog) -> OfferReidentifyService:
    return OfferReidentifyService(
        sources=FakeSources(),
        offers=catalog,
        identity=OfferIdentityRules(),
        clock=FakeClock(),
        page_size=2,
    )


async def check_transition_keeps_history() -> None:
    catalog = FakeOfferCatalog(
        [
            legacy_offer("Прокладка под рельс Р-50", EARLY),
            # То же самое с другой пунктуацией: после перехода это одна позиция.
            legacy_offer("Прокладка под рельс, Р-50", LATE),
            legacy_offer("Костыль путевой", EARLY),
        ]
    )
    result = await service(catalog).run()

    assert result.offers == 3, result
    assert result.changed == 3, result
    assert result.merged == 1, result
    # Три старых строки ушли, осталось две новых.
    assert len(catalog.rows) == 2, catalog.rows

    rows = {offer.name: offer for offer, _ in catalog.rows.values()}
    survivor = next(offer for offer, _ in catalog.rows.values() if "рельс" in offer.name)
    # Время первой встречи сохранено по самой ранней из слитых позиций.
    assert survivor.first_seen_at == EARLY, survivor
    assert survivor.last_seen_at == LATE, survivor
    assert survivor.external_id.startswith(f"{PAGE}#"), survivor.external_id
    assert len(survivor.external_id) < len(f"{PAGE}#Прокладка под рельс Р-50")
    assert survivor.offer_id == identity.offer_id(SOURCE_ID, survivor.external_id)
    assert "Костыль путевой" in rows


async def check_second_run_is_quiet() -> None:
    catalog = FakeOfferCatalog([legacy_offer("Прокладка под рельс Р-50", EARLY)])
    await service(catalog).run()
    before = {offer_id: offer for offer_id, (offer, _) in catalog.rows.items()}

    result = await service(catalog).run()
    # Правило уже применено: ключи те же, удалять нечего.
    assert result.changed == 0, result
    assert result.merged == 0, result
    assert {offer_id: offer for offer_id, (offer, _) in catalog.rows.items()} == before


async def check_source_key_untouched() -> None:
    offer = Offer(
        offer_id=identity.offer_id(SOURCE_ID, "4613"),
        source_id=SOURCE_ID,
        external_id="4613",
        url="https://shop.test/p/4613",
        name="Бумага офисная",
        first_seen_at=EARLY,
        last_seen_at=LATE,
    )
    catalog = FakeOfferCatalog([offer])
    result = await service(catalog).run()
    assert result.changed == 0, result
    assert next(iter(catalog.rows.values()))[0].external_id == "4613"


async def main() -> None:
    await check_transition_keeps_history()
    await check_second_run_is_quiet()
    await check_source_key_untouched()
    print("Проверка смены ключа идентичности пройдена")


if __name__ == "__main__":
    asyncio.run(main())
