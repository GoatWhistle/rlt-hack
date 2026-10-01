"""Репозиторий предложений."""

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.rows import to_datetime, to_uuid
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.offer import Offer

COLUMNS = (
    "offer_id",
    "source_id",
    "external_id",
    "supplier_id",
    "seller_status",
    "seller_evidence_url",
    "url",
    "name",
    "description",
    "item_type",
    "brand",
    "article",
    "attributes",
    "source_category",
    "okpd2_code",
    "price",
    "currency",
    "unit",
    "delivery_regions",
    "availability",
    "supplier_role",
    "role_evidence_url",
    "role_evidence_text",
    "content_hash",
    "first_seen_at",
    "last_seen_at",
    "updated_at",
    "version",
    "is_deleted",
)

# Предложения, которых нет в полном обходе, снимаются с продажи, а не удаляются:
# данные и свидетельства сохраняются. Пишется полный снимок строки новой версией.
# Фильтр лежит во вложенном запросе: псевдоним availability из REPLACE иначе
# перекрывает колонку в WHERE и условие становится всегда ложным.
_ABSENT_CONDITION = (
    "WHERE source_id = {source_id:UUID} "
    "AND availability != 'unavailable' "
    "AND NOT has({seen:Array(UUID)}, offer_id))"
)


class ClickHouseOfferRepository:
    def __init__(
        self,
        gateway: SqlGateway,
        versions: VersionSequencer,
        database: str = "supplier_search",
    ) -> None:
        self._gateway = gateway
        self._versions = versions
        self._db = database

    async def save_many(self, offers: Sequence[Offer]) -> None:
        updated_at = datetime.now(UTC)
        await self._gateway.insert(
            f"{self._db}.offers",
            COLUMNS,
            [
                (
                    offer.offer_id,
                    offer.source_id,
                    offer.external_id,
                    offer.supplier_id,
                    str(offer.seller_status),
                    offer.seller_evidence_url,
                    offer.url,
                    offer.name,
                    offer.description,
                    str(offer.item_type),
                    offer.brand,
                    offer.article,
                    dict(offer.attributes),
                    offer.source_category,
                    offer.okpd2_code,
                    offer.price,
                    offer.currency,
                    offer.unit,
                    list(offer.delivery_regions),
                    str(offer.availability),
                    str(offer.supplier_role),
                    offer.role_evidence_url,
                    offer.role_evidence_text,
                    offer.content_hash,
                    offer.first_seen_at,
                    offer.last_seen_at,
                    updated_at,
                    self._versions.next(),
                    0,
                )
                for offer in offers
            ],
        )

    async def first_seen(self, offer_ids: Iterable[UUID]) -> dict[UUID, datetime]:
        ids = [str(value) for value in offer_ids]
        if not ids:
            return {}
        rows = await self._gateway.select(
            f"SELECT offer_id, min(first_seen_at) FROM {self._db}.offers "
            "WHERE offer_id IN {offer_ids:Array(UUID)} GROUP BY offer_id",
            {"offer_ids": ids},
        )
        return {to_uuid(row[0]): to_datetime(row[1]) for row in rows}

    async def withdraw_absent(
        self,
        source_id: UUID,
        seen_offer_ids: Iterable[UUID],
        observed_at: datetime,
    ) -> int:
        parameters = {
            "source_id": str(source_id),
            "seen": [str(value) for value in seen_offer_ids],
            "withdrawn_at": observed_at,
            "version_floor": self._versions.next(),
        }
        source = f"FROM (SELECT * FROM {self._db}.offers_current " + _ABSENT_CONDITION
        counted = await self._gateway.select("SELECT count() " + source, parameters)
        absent = int(counted[0][0]) if counted else 0
        if absent == 0:
            return 0
        await self._gateway.command(
            f"INSERT INTO {self._db}.offers SELECT * REPLACE ("
            "'unavailable' AS availability, "
            "{withdrawn_at:DateTime64(3, 'UTC')} AS updated_at, "
            "greatest(version + 1, {version_floor:UInt64}) AS version) " + source,
            parameters,
        )
        return absent
