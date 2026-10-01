from src.adapter.repository.clickhouse.protocols import SqlGateway

PROBE_NAME = "clickhouse"


class ClickHouseProbe:
    def __init__(self, gateway: SqlGateway) -> None:
        self._gateway = gateway

    @property
    def name(self) -> str:
        return PROBE_NAME

    async def check(self) -> None:
        await self._gateway.select("SELECT 1")
