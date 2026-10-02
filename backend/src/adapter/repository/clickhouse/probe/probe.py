from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.errors import DatasetMissingError

PROBE_NAME = "clickhouse"
SELECT_OFFER = "SELECT 1 FROM {db}.offers LIMIT 1"
SELECT_EVIDENCE = "SELECT 1 FROM {db}.supplier_evidence_imports LIMIT 1"
SELECT_ROSTER = "SELECT 1 FROM {db}.archive_supplier_sets LIMIT 1"


class ClickHouseProbe:
    def __init__(self, gateway: SqlGateway) -> None:
        self._gateway = gateway

    @property
    def name(self) -> str:
        return PROBE_NAME

    @property
    def required(self) -> bool:
        return True

    async def check(self) -> None:
        await self._gateway.select("SELECT 1")


class DatasetProbe:
    def __init__(self, gateway: SqlGateway, name: str, statement: str, database: str) -> None:
        self._gateway = gateway
        self._name = name
        self._statement = statement.format(db=database)

    @classmethod
    def catalog(cls, gateway: SqlGateway, database: str) -> "DatasetProbe":
        return cls(gateway, "catalog", SELECT_OFFER, database)

    @classmethod
    def history(cls, gateway: SqlGateway, database: str) -> "DatasetProbe":
        return cls(gateway, "history", SELECT_EVIDENCE, database)

    @classmethod
    def novelty(cls, gateway: SqlGateway, database: str) -> "DatasetProbe":
        return cls(gateway, "novelty", SELECT_ROSTER, database)

    @property
    def name(self) -> str:
        return self._name

    @property
    def required(self) -> bool:
        return False

    async def check(self) -> None:
        if not await self._gateway.select(self._statement):
            raise DatasetMissingError(self._name)
