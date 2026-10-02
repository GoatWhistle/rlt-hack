"""Загрузка выгрузки реестра МСП в хранилище.

Выгрузка — полный снимок реестра на дату формирования. Пока она не прочитана
целиком, прежние сведения остаются: компании, выбывшие из реестра, удаляются
только после успешной загрузки всех файлов.

Выгрузка отдаёт около 900 компаний на XML-файл, а файлов — тысячи. Каждая
вставка создаёт в ClickHouse отдельную часть таблицы, поэтому компании
копятся в крупные пачки: тысячи мелких вставок упираются в лимит частей.
"""

import logging
from collections.abc import Sequence

from src.models.company.enrichment import RegistryImportResult
from src.models.company.registry import MspCompany
from src.service.errors import EmptyRegistryDumpError
from src.service.registry.protocols import RegistryDump, RegistryStore

logger = logging.getLogger(__name__)

BATCH_SIZE = 50_000


class RegistryImportService:
    def __init__(
        self,
        dump: RegistryDump,
        store: RegistryStore,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        self._dump = dump
        self._store = store
        self._batch_size = max(1, batch_size)

    async def run(self) -> RegistryImportResult:
        companies = 0
        latest = None
        pending: list[MspCompany] = []
        async for batch in self._dump.read():
            if not batch:
                continue
            pending.extend(batch)
            companies += len(batch)
            newest = max(company.registry_date for company in batch)
            latest = newest if latest is None else max(latest, newest)
            if len(pending) >= self._batch_size:
                await self._save(pending)
                pending = []
        await self._save(pending)
        if latest is None:
            raise EmptyRegistryDumpError("в выгрузке реестра МСП нет ни одной компании")
        await self._store.remove_older(latest)
        logger.info("Реестр МСП на %s: загружено компаний — %d", latest, companies)
        return RegistryImportResult(companies=companies, registry_date=latest)

    async def _save(self, companies: Sequence[MspCompany]) -> None:
        if companies:
            await self._store.save_many(companies)
            logger.info("Реестр МСП: записано компаний — %d", len(companies))
