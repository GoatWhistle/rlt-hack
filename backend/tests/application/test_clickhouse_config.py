import pytest

from src.application.config import AppConfig

VARIABLES = ("CLICKHOUSE_POOL_SIZE", "CLICKHOUSE_MAX_THREADS")


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
