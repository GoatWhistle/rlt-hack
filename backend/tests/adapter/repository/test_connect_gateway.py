from dataclasses import dataclass, field

from src.adapter.repository.clickhouse.engine.gateway import ConnectGateway


@dataclass(slots=True)
class QueryResult:
    result_rows: list[tuple[object, ...]] = field(default_factory=list)


@dataclass(slots=True)
class RecordingClient:
    settings: list[dict[str, str]] = field(default_factory=list)

    def query(
        self, statement: str, parameters: dict[str, object], settings: dict[str, str]
    ) -> QueryResult:
        self.settings.append(settings)
        return QueryResult([(1,)])


async def test_queries_carry_the_request_id_as_log_comment() -> None:
    client = RecordingClient()
    assert await ConnectGateway(client, lambda: "trace-0001").select("SELECT 1") == [(1,)]
    await ConnectGateway(client, lambda: None).select("SELECT 1")
    await ConnectGateway(client).select("SELECT 1")
    first, second, third = client.settings
    assert first["log_comment"] == "trace-0001"
    assert "log_comment" not in second
    assert "log_comment" not in third
    assert len({first["query_id"], second["query_id"], third["query_id"]}) == 3
