from dataclasses import replace

import pytest

from src.adapter.repository.clickhouse.client import session_settings
from src.adapter.repository.clickhouse.config import ClickHouseConfig
from src.application.config import ApiStorageConfig, AppConfig, api_clickhouse

VARIABLES = (
    "CLICKHOUSE_POOL_SIZE",
    "CLICKHOUSE_MAX_THREADS",
    "CLICKHOUSE_API_QUERY_TIMEOUT",
    "CLICKHOUSE_BACKGROUND_POOL_SIZE",
    "CLICKHOUSE_API_MAX_MEMORY_USAGE",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_pool_defaults(clean_env: pytest.MonkeyPatch) -> None:
    clickhouse = AppConfig.from_env().clickhouse
    assert (clickhouse.pool_size, clickhouse.max_threads) == (4, 4)


def test_pool_is_read_from_environment(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("CLICKHOUSE_POOL_SIZE", "8")
    clean_env.setenv("CLICKHOUSE_MAX_THREADS", "0")
    clickhouse = AppConfig.from_env().clickhouse
    assert (clickhouse.pool_size, clickhouse.max_threads) == (8, 0)


def test_job_client_has_no_execution_limit() -> None:
    assert session_settings(ClickHouseConfig()) == {"insert_deduplicate": 0, "max_threads": 4}


@pytest.mark.parametrize(
    ("budget", "execution", "timeout"), [(8.0, 10, 15), (30.0, 32, 34), (0.5, 3, 15)]
)
def test_api_client_limits_execution_time(budget: float, execution: int, timeout: int) -> None:
    config = api_clickhouse(ClickHouseConfig(query_timeout=300), ApiStorageConfig(), budget)
    assert (config.max_execution_time, config.query_timeout) == (execution, timeout)
    settings = session_settings(config)
    assert settings["max_execution_time"] == execution
    assert settings["timeout_overflow_mode"] == "throw"
    assert "max_memory_usage" not in settings


def test_api_client_memory_limit_is_optional() -> None:
    storage = replace(ApiStorageConfig(), max_memory_usage=500_000_000)
    config = api_clickhouse(ClickHouseConfig(), storage, 8.0)
    assert session_settings(config)["max_memory_usage"] == 500_000_000


def test_api_storage_is_read_from_environment(clean_env: pytest.MonkeyPatch) -> None:
    assert AppConfig.from_env().api_storage == ApiStorageConfig()
    clean_env.setenv("CLICKHOUSE_API_QUERY_TIMEOUT", "20")
    clean_env.setenv("CLICKHOUSE_BACKGROUND_POOL_SIZE", "1")
    clean_env.setenv("CLICKHOUSE_API_MAX_MEMORY_USAGE", "1000")
    storage = AppConfig.from_env().api_storage
    assert (storage.query_timeout, storage.background_pool_size, storage.max_memory_usage) == (
        20,
        1,
        1000,
    )
