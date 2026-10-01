"""Подключение к ClickHouse."""

import asyncio
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.exceptions import ClickHouseError

from src.adapter.repository.clickhouse.config import ClickHouseConfig
from src.adapter.repository.errors import RepositoryUnavailableError


async def create_client(config: ClickHouseConfig) -> Any:
    """Создаёт клиент ClickHouse. Соединение проверяется сразу.

    Драйвер синхронный, поэтому подключение выполняется в отдельном потоке:
    событийный цикл не блокируется ожиданием сети.
    """
    return await asyncio.to_thread(_connect, config)


def _connect(config: ClickHouseConfig) -> Any:
    """Запросы к несуществующей БД допустимы до применения миграций, поэтому
    клиент подключается без выбора базы: имя схемы указано в запросах."""
    try:
        return clickhouse_connect.get_client(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            secure=config.secure,
            connect_timeout=config.connect_timeout,
            send_receive_timeout=config.query_timeout,
            settings=session_settings(config),
        )
    except ClickHouseError as error:
        raise RepositoryUnavailableError(str(error)) from error
    except OSError as error:
        raise RepositoryUnavailableError(str(error)) from error


def session_settings(config: ClickHouseConfig) -> dict[str, int | str]:
    settings: dict[str, int | str] = {"insert_deduplicate": 0}
    if config.max_threads > 0:
        settings["max_threads"] = config.max_threads
    if config.max_execution_time > 0:
        settings["max_execution_time"] = config.max_execution_time
        settings["timeout_overflow_mode"] = "throw"
    if config.max_memory_usage > 0:
        settings["max_memory_usage"] = config.max_memory_usage
    return settings
