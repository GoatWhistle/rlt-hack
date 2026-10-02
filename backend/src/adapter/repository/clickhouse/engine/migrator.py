"""Применение SQL-миграций ClickHouse из каталога migration."""

import asyncio
import hashlib
import logging
import re
from pathlib import Path

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.errors import MigrationError

logger = logging.getLogger(__name__)

MIGRATION_DIR = Path(__file__).resolve().parents[5] / "migration"

_COMMENT = re.compile(r"--[^\n]*")


def split_statements(sql: str) -> list[str]:
    """Делит файл на запросы. Строковых литералов с `--` и `;` в миграциях нет."""
    return [part.strip() for part in _COMMENT.sub("", sql).split(";") if part.strip()]


class Migrator:
    """Выполняет непримененные файлы по возрастанию имени и фиксирует их.

    Имя файла — номер и описание: `0001_initial_schema.sql`. Изменять
    применённый файл нельзя: расхождение контрольной суммы останавливает работу.
    """

    def __init__(
        self,
        gateway: SqlGateway,
        migrations_dir: Path = MIGRATION_DIR,
        database: str = "supplier_search",
    ) -> None:
        self._gateway = gateway
        self._dir = migrations_dir
        self._database = database

    async def apply_pending(self) -> list[str]:
        await self._bootstrap()
        applied = await self._applied()
        executed: list[str] = []
        for path in self._files():
            sql = await asyncio.to_thread(path.read_text, encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            known = applied.get(path.name)
            if known == checksum:
                continue
            if known is not None:
                raise MigrationError(
                    f"{path.name} изменён после применения: нужен новый файл миграции"
                )
            statements = split_statements(sql)
            if not statements:
                raise MigrationError(f"{path.name} не содержит запросов")
            logger.info("Применяется миграция %s (%d запросов)", path.name, len(statements))
            for statement in statements:
                await self._gateway.command(statement)
            await self._record(path.name, checksum, len(statements))
            executed.append(path.name)
        return executed

    async def applied_names(self) -> list[str]:
        await self._bootstrap()
        return sorted(await self._applied())

    def _files(self) -> list[Path]:
        if not self._dir.is_dir():
            raise MigrationError(f"каталог миграций не найден: {self._dir}")
        return sorted(self._dir.glob("*.sql"))

    async def _bootstrap(self) -> None:
        await self._gateway.command(f"CREATE DATABASE IF NOT EXISTS {self._database}")
        await self._gateway.command(
            f"CREATE TABLE IF NOT EXISTS {self._database}.schema_migrations "
            "(name String, checksum String, statements UInt32, "
            "applied_at DateTime64(3, 'UTC') DEFAULT now64(3)) "
            "ENGINE = ReplacingMergeTree ORDER BY name"
        )

    async def _applied(self) -> dict[str, str]:
        rows = await self._gateway.select(
            f"SELECT name, checksum FROM {self._database}.schema_migrations FINAL"
        )
        return {str(name): str(checksum) for name, checksum in rows}

    async def _record(self, name: str, checksum: str, statements: int) -> None:
        await self._gateway.insert(
            f"{self._database}.schema_migrations",
            ("name", "checksum", "statements"),
            [(name, checksum, statements)],
        )
