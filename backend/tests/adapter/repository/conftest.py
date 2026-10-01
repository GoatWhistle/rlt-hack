from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR, Migrator
from tests.clickhouse.chdb_gateway import ChdbGateway


@pytest.fixture
async def gateway(tmp_path: Path) -> AsyncIterator[ChdbGateway]:
    engine = pytest.importorskip("chdb.session")
    session = engine.Session(str(tmp_path / "chdb"))
    gateway = ChdbGateway(session)
    await Migrator(gateway, MIGRATION_DIR).apply_pending()
    yield gateway
    session.close()
