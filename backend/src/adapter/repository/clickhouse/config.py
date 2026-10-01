"""Параметры подключения к ClickHouse. Драйвер здесь не импортируется."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClickHouseConfig:
    host: str = "localhost"
    port: int = 8123
    username: str = "default"
    password: str = ""
    database: str = "supplier_search"
    secure: bool = False
    connect_timeout: int = 10
    query_timeout: int = 300
