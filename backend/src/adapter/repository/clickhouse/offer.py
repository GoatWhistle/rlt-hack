"""Репозиторий предложений.

Производные значения нормализации и классификации пишутся теми же строками,
что и исходные поля: версия строки одна, поэтому рассинхронизации исходника и
производного не возникает.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.rows import (
    to_datetime,
    to_decimal,
    to_optional_uuid,
    to_uuid,
)
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.classification import Classification
from src.models.coverage import CoverageReport, Share
from src.models.enums import (
    Availability,
    ClassificationMethod,
    ItemType,
    SupplierRole,
    VerificationStatus,
)
from src.models.normalization import Normalization
from src.models.offer import Offer

COLUMNS = (
    "offer_id",
    "source_id",
    "external_id",
    "supplier_id",
    "seller_status",
    "evidence_url",
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
    "availability",
    "supplier_role",
    "role_evidence_text",
    "content_hash",
    "first_seen_at",
    "last_seen_at",
    "normalized_name",
    "normalized_key",
    "normalized_attributes",
    "unit_code",
    "unit_name",
    "price_per_unit",
    "price_unit_code",
    "normalizer_version",
    "okpd2_level",
    "rubric",
    "rubric_name",
    "classification_method",
    "classification_confidence",
    "classification_evidence",
    "classifier_version",
    "updated_at",
    "version",
    "is_deleted",
)
# Колонки состояния строки заполняет сам репозиторий: читать их в модель незачем.
STATE_COLUMNS = ("updated_at", "version", "is_deleted")
READ_COLUMNS = tuple(name for name in COLUMNS if name not in STATE_COLUMNS)

# Предложения, которых нет в полном обходе, снимаются с продажи, а не удаляются:
# данные и свидетельства сохраняются. Пишется полный снимок строки новой версией.
# Отсутствующие отбираются по времени обхода: все строки пакета записаны с его
# отметкой, поэтому более старая отметка означает, что предложение не встретилось.
# Перечислять увиденные идентификаторы нельзя — пакет каталога их тысячи, а
# параметры запроса уходят в HTTP-форму с ограниченной длиной поля.
# Фильтр лежит во вложенном запросе: псевдоним availability из REPLACE иначе
# перекрывает колонку в WHERE и условие становится всегда ложным.
_ABSENT_CONDITION = (
    "WHERE source_id = {source_id:UUID} "
    "AND availability != 'unavailable' "
    "AND updated_at < {observed_at:DateTime64(3, 'UTC')})"
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

    async def save_many(self, offers: Sequence[Offer], updated_at: datetime) -> None:
        """Отметка обхода общая для всего пакета: по ней отбираются исчезнувшие."""
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
                    offer.evidence_url,
                    offer.url,
                    offer.name,
                    offer.description,
                    str(offer.item_type),
                    _brand(offer),
                    _article(offer),
                    dict(offer.attributes),
                    offer.source_category,
                    _code(offer),
                    offer.price,
                    _currency(offer),
                    offer.unit,
                    str(offer.availability),
                    str(offer.supplier_role),
                    offer.role_evidence_text,
                    offer.content_hash,
                    offer.first_seen_at,
                    offer.last_seen_at,
                    *_derived(offer),
                    updated_at,
                    self._versions.next(),
                    0,
                )
                for offer in offers
            ],
        )

    async def first_seen(self, source_id: UUID) -> dict[UUID, datetime]:
        """Время первой встречи всех предложений источника: оно не теряется."""
        rows = await self._gateway.select(
            f"SELECT offer_id, min(first_seen_at) FROM {self._db}.offers "
            "WHERE source_id = {source_id:UUID} GROUP BY offer_id",
            {"source_id": str(source_id)},
        )
        return {to_uuid(row[0]): to_datetime(row[1]) for row in rows}

    async def withdraw_absent(self, source_id: UUID, observed_at: datetime) -> int:
        parameters = {
            "source_id": str(source_id),
            "observed_at": observed_at,
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

    async def delete_stale(self, source_id: UUID, written_at: datetime) -> int:
        """Помечает удалёнными строки источника, не переписанные этим проходом.

        Отбор идёт по отметке времени: идентификаторов тысячи, и списком они в
        параметры запроса не помещаются. Данные остаются в таблице прежними
        версиями — удаляется только актуальность строки.
        """
        parameters = {
            "source_id": str(source_id),
            "written_at": written_at,
            "version_floor": self._versions.next(),
        }
        source = (
            f"FROM (SELECT * FROM {self._db}.offers_current "
            "WHERE source_id = {source_id:UUID} "
            "AND updated_at < {written_at:DateTime64(3, 'UTC')})"
        )
        counted = await self._gateway.select("SELECT count() " + source, parameters)
        stale = int(counted[0][0]) if counted else 0
        if stale == 0:
            return 0
        await self._gateway.command(
            f"INSERT INTO {self._db}.offers SELECT * REPLACE ("
            "1 AS is_deleted, "
            "{written_at:DateTime64(3, 'UTC')} AS updated_at, "
            "greatest(version + 1, {version_floor:UInt64}) AS version) " + source,
            parameters,
        )
        return stale

    async def list_by_source(self, source_id: UUID, limit: int, offset: int) -> list[Offer]:
        """Страница актуальных предложений источника в устойчивом порядке."""
        rows = await self._gateway.select(
            f"SELECT {', '.join(READ_COLUMNS)} FROM {self._db}.offers_current "
            "WHERE source_id = {source_id:UUID} ORDER BY offer_id "
            "LIMIT {limit:UInt32} OFFSET {offset:UInt64}",
            {"source_id": str(source_id), "limit": limit, "offset": offset},
        )
        return [_to_offer(row) for row in rows]

    async def coverage(self) -> CoverageReport:
        """Сводка заполненности: метрика подготовки данных, а не модели."""
        totals = await self._gateway.select(
            "SELECT count(), countIf(normalizer_version != ''), countIf(okpd2_code != ''), "
            "countIf(rubric != ''), countIf(unit_code != ''), countIf(price_per_unit IS NOT NULL), "
            "countIf(brand != ''), countIf(article != ''), "
            "countIf(length(normalized_attributes) > 0) "
            f"FROM {self._db}.offers_current"
        )
        row = totals[0] if totals else (0,) * 9
        return CoverageReport(
            offers=int(row[0]),
            normalized=int(row[1]),
            classified=int(row[2]),
            with_rubric=int(row[3]),
            with_unit=int(row[4]),
            with_price_per_unit=int(row[5]),
            with_brand=int(row[6]),
            with_article=int(row[7]),
            with_attributes=int(row[8]),
            by_method=await self._shares("classification_method"),
            by_rubric=await self._shares("rubric"),
            by_item_type=await self._shares("item_type"),
            by_level=await self._shares("toString(okpd2_level)"),
        )

    async def _shares(self, expression: str) -> tuple[Share, ...]:
        rows = await self._gateway.select(
            f"SELECT {expression} AS name, count() AS offers FROM {self._db}.offers_current "
            "GROUP BY name ORDER BY offers DESC"
        )
        return tuple(Share(name=str(name), offers=int(offers)) for name, offers in rows)


def _brand(offer: Offer) -> str:
    """Бренд, найденный разбором, не теряется: он полнее поля источника."""
    normalization = offer.normalization
    return normalization.brand if normalization and normalization.brand else offer.brand


def _article(offer: Offer) -> str:
    """Артикул разбор чаще находит в самом названии, чем отдаёт источник."""
    normalization = offer.normalization
    return normalization.article if normalization and normalization.article else offer.article


def _currency(offer: Offer) -> str:
    """Код валюты по ISO: разнобой источников до хранилища не доходит."""
    normalization = offer.normalization
    return normalization.currency if normalization and normalization.currency else offer.currency


def _code(offer: Offer) -> str:
    """Код классификации главнее исходного поля.

    Канал gold копирует в классификацию код самого источника, поэтому значение
    колонки всегда совпадает с тем, что объясняют метод и основание.
    """
    classification = offer.classification
    if classification and classification.okpd2_code:
        return classification.okpd2_code
    return offer.okpd2_code


def _derived(offer: Offer) -> tuple[object, ...]:
    """Производные поля в порядке COLUMNS; без разбора они остаются пустыми."""
    normalization = offer.normalization or Normalization()
    classification = offer.classification or Classification()
    return (
        normalization.name,
        normalization.key,
        dict(normalization.attributes),
        normalization.unit_code,
        normalization.unit_name,
        normalization.price_per_unit,
        normalization.price_unit_code,
        normalization.algorithm_version,
        classification.okpd2_level,
        classification.rubric_code,
        classification.rubric_name,
        str(classification.method),
        classification.confidence,
        classification.evidence,
        classification.algorithm_version,
    )


def _to_offer(row: Sequence[object]) -> Offer:
    """Собирает модель из строки хранилища.

    Код ОКПД2 возвращается в поле предложения только тогда, когда он пришёл от
    самого источника. Код, проставленный классификатором, остаётся в
    классификации: иначе при повторном разборе он выглядел бы кодом источника и
    канал больше никогда не пересчитывался бы.
    """
    values = dict(zip(READ_COLUMNS, row, strict=True))
    method = ClassificationMethod(str(values["classification_method"] or "none"))
    stored_code = str(values["okpd2_code"])
    from_source = method in (ClassificationMethod.GOLD, ClassificationMethod.NONE)
    source_code = stored_code if from_source else ""
    return Offer(
        offer_id=to_uuid(values["offer_id"]),
        source_id=to_uuid(values["source_id"]),
        external_id=str(values["external_id"]),
        supplier_id=to_optional_uuid(values["supplier_id"]),
        seller_status=VerificationStatus(str(values["seller_status"])),
        evidence_url=str(values["evidence_url"]),
        url=str(values["url"]),
        name=str(values["name"]),
        description=str(values["description"]),
        item_type=ItemType(str(values["item_type"])),
        brand=str(values["brand"]),
        article=str(values["article"]),
        attributes=dict(values["attributes"] or {}),
        source_category=str(values["source_category"]),
        okpd2_code=source_code,
        price=to_decimal(values["price"]),
        currency=str(values["currency"]),
        unit=str(values["unit"]),
        availability=Availability(str(values["availability"])),
        supplier_role=SupplierRole(str(values["supplier_role"])),
        role_evidence_text=str(values["role_evidence_text"]),
        content_hash=str(values["content_hash"]),
        first_seen_at=to_datetime(values["first_seen_at"]),
        last_seen_at=to_datetime(values["last_seen_at"]),
        normalization=Normalization(
            name=str(values["normalized_name"]),
            key=str(values["normalized_key"]),
            brand=str(values["brand"]),
            article=str(values["article"]),
            attributes=dict(values["normalized_attributes"] or {}),
            unit_code=str(values["unit_code"]),
            unit_name=str(values["unit_name"]),
            price_per_unit=to_decimal(values["price_per_unit"]),
            price_unit_code=str(values["price_unit_code"]),
            currency=str(values["currency"]),
            algorithm_version=str(values["normalizer_version"]),
        ),
        classification=Classification(
            okpd2_code=stored_code,
            okpd2_level=int(values["okpd2_level"] or 0),
            rubric_code=str(values["rubric"]),
            rubric_name=str(values["rubric_name"]),
            item_type=ItemType(str(values["item_type"])),
            method=method,
            confidence=float(values["classification_confidence"] or 0.0),
            evidence=str(values["classification_evidence"]),
            algorithm_version=str(values["classifier_version"]),
        ),
    )
