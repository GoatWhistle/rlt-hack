import pytest

from src.application.config import ApiConfig, AppConfig, MlServiceConfig, SearchConfig

VARIABLES = (
    "API_HOST",
    "API_PORT",
    "API_DOCS",
    "SEARCH_TIMEOUT_SECONDS",
    "SEARCH_ARCHIVE_TIMEOUT_SECONDS",
    "SEARCH_RETRIEVAL_DEPTH",
    "SEARCH_COVERAGE_THRESHOLD",
    "SEARCH_LEXICAL_POOL",
    "SEARCH_HISTORY_ENABLED",
    "SEARCH_ML_ENABLED",
    "ML_SERVICE_URL",
    "ML_SERVICE_TIMEOUT",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults_without_environment(clean_env: pytest.MonkeyPatch) -> None:
    config = AppConfig.from_env()
    assert config.api == ApiConfig(host="0.0.0.0", port=8000, docs_enabled=True)
    assert config.search == SearchConfig(
        timeout_seconds=15.0,
        retrieval_depth_factor=3,
        coverage_threshold=0.5,
        lexical_pool=500,
        history_enabled=True,
    )
    assert config.ml_service == MlServiceConfig(
        enabled=False, base_url="http://ml:8001", timeout_seconds=5.0
    )
    assert AppConfig().api == config.api


def test_empty_values_fall_back_to_defaults(clean_env: pytest.MonkeyPatch) -> None:
    for name in VARIABLES:
        clean_env.setenv(name, "")
    config = AppConfig.from_env()
    assert config.api == ApiConfig()
    assert config.search == SearchConfig()
    assert config.ml_service == MlServiceConfig()


def test_values_are_read_from_environment(clean_env: pytest.MonkeyPatch) -> None:
    values = {
        "API_HOST": "127.0.0.1",
        "API_PORT": "9000",
        "API_DOCS": "false",
        "SEARCH_TIMEOUT_SECONDS": "2.5",
        "SEARCH_ARCHIVE_TIMEOUT_SECONDS": "4.5",
        "SEARCH_RETRIEVAL_DEPTH": "4",
        "SEARCH_COVERAGE_THRESHOLD": "0.75",
        "SEARCH_LEXICAL_POOL": "200",
        "SEARCH_HISTORY_ENABLED": "no",
        "SEARCH_ML_ENABLED": "true",
        "ML_SERVICE_URL": "http://localhost:8001",
        "ML_SERVICE_TIMEOUT": "1.5",
    }
    for name, value in values.items():
        clean_env.setenv(name, value)
    config = AppConfig.from_env()
    assert config.api == ApiConfig(host="127.0.0.1", port=9000, docs_enabled=False)
    assert config.search == SearchConfig(
        timeout_seconds=2.5,
        archive_timeout_seconds=4.5,
        retrieval_depth_factor=4,
        coverage_threshold=0.75,
        lexical_pool=200,
        history_enabled=False,
    )
    assert config.ml_service == MlServiceConfig(
        enabled=True, base_url="http://localhost:8001", timeout_seconds=1.5
    )
