"""Чтение ZIP-выгрузки реестра МСП с открытых данных ФНС.

Выгрузка весит около 2 ГБ и скачивается заранее: сервер ФНС ограничивает
скорость соединения, поэтому загрузка в рамках команды заняла бы часы. Архив
разбирается по одному XML-файлу в пуле потоков, а компании отдаются пачкой на
файл — хранилище пишет их, пока разбирается следующий.
"""

import asyncio
import logging
import zipfile
import zlib
from collections.abc import AsyncIterator
from pathlib import Path

from lxml import etree

from src.adapter.client.errors import RegistryDumpError
from src.adapter.client.msp_registry.document import parse_stream
from src.models.company.registry import MspCompany

logger = logging.getLogger(__name__)


class MspRegistryDump:
    def __init__(self, path: Path) -> None:
        self._path = path

    async def read(self) -> AsyncIterator[list[MspCompany]]:
        members = await asyncio.to_thread(self._members)
        for index, member in enumerate(members, start=1):
            companies = await asyncio.to_thread(self._parse, member)
            logger.info(
                "Реестр МСП: файл %d из %d, компаний — %d", index, len(members), len(companies)
            )
            yield companies

    def _members(self) -> list[str]:
        if not self._path.is_file():
            raise RegistryDumpError(f"выгрузка реестра МСП не найдена: {self._path}")
        try:
            with zipfile.ZipFile(self._path) as archive:
                members = sorted(
                    name for name in archive.namelist() if name.lower().endswith(".xml")
                )
        except zipfile.BadZipFile as error:
            raise RegistryDumpError(f"{self._path.name}: архив повреждён: {error}") from error
        if not members:
            raise RegistryDumpError(f"{self._path.name}: в архиве нет XML-файлов")
        return members

    def _parse(self, member: str) -> list[MspCompany]:
        try:
            with zipfile.ZipFile(self._path) as archive, archive.open(member) as stream:
                return parse_stream(stream)
        except (zipfile.BadZipFile, zlib.error, etree.XMLSyntaxError, OSError) as error:
            raise RegistryDumpError(f"{member}: не разбирается: {error}") from error
