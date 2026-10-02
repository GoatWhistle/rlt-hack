from bench.clickhouse import ClickHouseHttp
from bench.sql import quote

STAGES = (
    ("lexical", "FROM supplier_search.offers_current AS o"),
    ("history", "ARRAY JOIN m.participants"),
    ("participation", "FROM supplier_search.supplier_lots"),
    ("offer_read", "INNER JOIN supplier_search.sources_current AS s"),
    ("suppliers", "FROM supplier_search.suppliers_current WHERE supplier_id IN"),
    ("archive", "INSERT INTO supplier_search.searches"),
)

BREAKDOWN = """
SELECT {stage} AS stage, count() AS queries,
    round(quantile(0.5)(query_duration_ms)) AS p50_ms,
    round(quantile(0.95)(query_duration_ms)) AS p95_ms,
    max(query_duration_ms) AS max_ms,
    round(avg(read_rows)) AS avg_read_rows,
    round(avg(memory_usage) / 1048576, 1) AS avg_memory_mib
FROM system.query_log
WHERE type = 'QueryFinish' AND event_time >= toDateTime({started})
    AND event_time <= toDateTime({finished})
    AND http_user_agent LIKE 'clickhouse-connect%'
GROUP BY stage
ORDER BY p95_ms DESC
"""


def _stage_expression() -> str:
    branches = ", ".join(
        f"position(query, {quote(marker)}) > 0, {quote(name)}" for name, marker in STAGES
    )
    return f"multiIf({branches}, 'other')"


async def breakdown(
    clickhouse: ClickHouseHttp, started: int, finished: int
) -> list[dict[str, object]]:
    await clickhouse.execute("SYSTEM FLUSH LOGS")
    statement = BREAKDOWN.format(stage=_stage_expression(), started=started, finished=finished)
    return await clickhouse.rows(statement)
