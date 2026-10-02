"""Чтение архива закупок: пары «название позиции — код ОКПД2».

Индекс строится в сервисе один раз на запуск, поэтому репозиторий отдаёт
названия пачкой, а не отвечает на тысячи одиночных запросов.
"""

from src.adapter.repository.clickhouse.protocols import SqlGateway


class ClickHouseArchiveRepository:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def load_items(self, limit: int) -> list[tuple[str, str]]:
        rows = await self._gateway.select(
            "SELECT product_name, okpd2_code "
            f"FROM {self._db}.procurement_items_current "
            "WHERE okpd2_code != '' AND product_name != '' "
            "LIMIT {limit:UInt64}",
            {"limit": limit},
        )
        return [(str(name), str(code)) for name, code in rows]
