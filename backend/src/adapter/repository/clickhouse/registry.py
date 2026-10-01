"""Реестр субъектов МСП в ClickHouse: загрузка выгрузки и поиск компаний по ИНН."""

from collections.abc import Sequence
from datetime import date
from typing import Any

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.registry import MspCompany

COLUMNS = (
    "inn",
    "name",
    "registry_date",
    "okved_main",
    "okved_main_name",
    "okved_main_reported",
    "okved_extra",
    "products",
)

# ИНН уходят параметром запроса, а он передаётся HTTP-формой ограниченной длины.
LOOKUP_BATCH = 500


class ClickHouseMspRegistryRepository:
    def __init__(
        self,
        gateway: SqlGateway,
        database: str = "supplier_search",
        lookup_batch: int = LOOKUP_BATCH,
    ) -> None:
        self._gateway = gateway
        self._db = database
        self._lookup_batch = max(1, lookup_batch)

    async def save_many(self, companies: Sequence[MspCompany]) -> None:
        await self._gateway.insert(
            f"{self._db}.msp_companies",
            COLUMNS,
            [
                (
                    company.inn,
                    company.name,
                    company.registry_date,
                    company.okved_main,
                    company.okved_main_name,
                    int(company.okved_main_reported),
                    list(company.okved_extra),
                    list(company.products),
                )
                for company in companies
            ],
        )

    async def remove_older(self, registry_date: date) -> None:
        """Компании прежних выгрузок, не попавшие в новую, выбыли из реестра."""
        await self._gateway.command(
            f"DELETE FROM {self._db}.msp_companies WHERE registry_date < {{day:Date}}",
            {"day": registry_date.isoformat()},
        )

    async def find(self, inns: Sequence[str]) -> dict[str, MspCompany]:
        unique = sorted(set(inns))
        found: dict[str, MspCompany] = {}
        for start in range(0, len(unique), self._lookup_batch):
            rows = await self._gateway.select(
                f"SELECT {', '.join(COLUMNS)} FROM {self._db}.msp_companies FINAL "
                "WHERE inn IN {inns:Array(String)}",
                {"inns": unique[start : start + self._lookup_batch]},
            )
            for row in rows:
                company = _company(row)
                found[company.inn] = company
        return found


def _company(row: Sequence[Any]) -> MspCompany:
    (
        inn,
        name,
        registry_date,
        okved_main,
        okved_main_name,
        okved_main_reported,
        okved_extra,
        products,
    ) = row
    return MspCompany(
        inn=str(inn),
        name=str(name),
        registry_date=(
            registry_date if isinstance(registry_date, date) else date.fromisoformat(registry_date)
        ),
        okved_main=str(okved_main),
        okved_main_name=str(okved_main_name),
        okved_main_reported=bool(int(okved_main_reported)),
        okved_extra=tuple(str(code) for code in okved_extra),
        products=tuple(str(code) for code in products),
    )
