"""Конфигурация приложения из переменных окружения.

Каждый адаптер источника включается своим флагом: обходятся только включённые.
Адреса и разметка источников живут в адаптерах, поэтому здесь остаются ключи
развёртывания — пути к данным, списки адресов и ограничения запуска.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from src.adapter.repository.clickhouse.config import ClickHouseConfig
from src.adapter.repository.reference import REFERENCE_DIR

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _optional_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    return Path(value) if value else None


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw and raw.strip() else default


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _urls(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(part.strip() for part in raw.replace("\n", ",").split(",") if part.strip())


def _dataset_path() -> Path:
    explicit = os.getenv("SUPPLIER_DATASET_PATH")
    if explicit:
        return Path(explicit).expanduser()
    # В контейнере каталог данных монтируется отдельно: путь задаётся переменной.
    data_dir = Path(os.getenv("TASK_DATA_DIR") or REPOSITORY_ROOT / "task/data")
    return data_dir / "Поставщики_24-25.csv"


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Только данные: конфигурация передаётся в контейнер зависимостей целиком."""

    clickhouse: ClickHouseConfig = field(default_factory=ClickHouseConfig)
    # Каталог справочников ОКПД2, рубрик, словаря, разделов каталогов и ОКЕИ.
    reference_dir: Path = REFERENCE_DIR
    # Канал переноса кода из архива закупок: без загруженного архива он пуст.
    use_archive_channel: bool = True
    archive_limit: int = 500_000
    dataset_path: Path = field(default_factory=_dataset_path)
    dataset_region: str = ""
    # Адреса фидов и сайтов поставщиков: по адаптеру на адрес.
    feed_urls: tuple[str, ...] = ()
    site_urls: tuple[str, ...] = ()
    request_timeout: float = 30.0
    # Сколько источников обходится одновременно.
    parallel_sources: int = 4
    # Сколько запросов к одному источнику выполняет его адаптер одновременно.
    parallel_requests: int = 4
    write_batch_size: int = 500
    sync_interval_seconds: float = 3600.0
    # Сколько карточек берёт с источника один обход: каталоги публикуют тысячи.
    max_cards_per_source: int = 500
    log_level: str = "INFO"
    use_supplier_dataset_provider: bool = True
    use_yml_feed_provider: bool = False
    use_schema_org_provider: bool = False
    # Селекторы каталогов не сверены с живыми страницами: по умолчанию выключены.
    use_optkatalog_provider: bool = False
    use_aboutpartner_provider: bool = False
    use_texzakaz_provider: bool = False
    # Сайт закрыт проверкой на робота: включается только с разрешения владельца.
    use_pulscen_provider: bool = False
    pulscen_delay_seconds: float = 10.0
    # Диагностический снимок страниц Пульса цен из JSON-файла: пусто — выключен.
    pulscen_snapshot_path: Path | None = None
    use_gisp_registry_provider: bool = False
    gisp_export_location: str = ""
    use_productcenter_provider: bool = False
    productcenter_max_cards: int = 0
    productcenter_parallel_requests: int = 1
    productcenter_request_interval: float = 1.0
    productcenter_connection_retries: int = 180
    productcenter_cache_dir: Path | None = None
    use_moscow_suppliers_provider: bool = False
    moscow_suppliers_export_url: str = ""
    use_supl_biz_provider: bool = False
    supl_biz_max_cards: int = 0

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            clickhouse=ClickHouseConfig(
                host=os.getenv("CLICKHOUSE_HOST", "localhost"),
                port=_int("CLICKHOUSE_PORT", 8123),
                username=os.getenv("CLICKHOUSE_USER", "default"),
                password=os.getenv("CLICKHOUSE_PASSWORD", ""),
                database=os.getenv("CLICKHOUSE_DATABASE", "supplier_search"),
                secure=_bool("CLICKHOUSE_SECURE", False),
            ),
            reference_dir=Path(os.getenv("REFERENCE_DIR") or REFERENCE_DIR),
            use_archive_channel=_bool("CLASSIFIER_ARCHIVE_CHANNEL", True),
            archive_limit=_int("CLASSIFIER_ARCHIVE_LIMIT", 500_000),
            dataset_path=_dataset_path(),
            dataset_region=os.getenv("SUPPLIER_DATASET_REGION", ""),
            feed_urls=_urls("SUPPLIER_FEED_URLS"),
            site_urls=_urls("SUPPLIER_SITE_URLS"),
            request_timeout=_float("REQUEST_TIMEOUT", 30.0),
            parallel_sources=_int("SYNC_PARALLEL_SOURCES", 4),
            parallel_requests=_int("SYNC_PARALLEL_REQUESTS", 4),
            write_batch_size=_int("SYNC_WRITE_BATCH", 500),
            max_cards_per_source=_int("SYNC_MAX_CARDS", 500),
            sync_interval_seconds=_float("SYNC_INTERVAL_SECONDS", 3600.0),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            use_supplier_dataset_provider=_bool("SUPPLIER_DATASET_PROVIDER", True),
            use_yml_feed_provider=_bool("YML_FEED_PROVIDER", False),
            use_schema_org_provider=_bool("SCHEMA_ORG_WEB_PROVIDER", False),
            use_optkatalog_provider=_bool("OPTKATALOG_WEB_PROVIDER", False),
            use_aboutpartner_provider=_bool("ABOUTPARTNER_WEB_PROVIDER", False),
            use_texzakaz_provider=_bool("TEXZAKAZ_WEB_PROVIDER", False),
            use_pulscen_provider=_bool("PULSCEN_WEB_PROVIDER", False),
            pulscen_delay_seconds=_float("PULSCEN_DELAY_SECONDS", 10.0),
            pulscen_snapshot_path=_optional_path("PULSCEN_SNAPSHOT_PATH"),
            use_gisp_registry_provider=_bool("GISP_REGISTRY_PROVIDER", False),
            gisp_export_location=os.getenv("GISP_EXPORT_LOCATION", ""),
            use_productcenter_provider=_bool("PRODUCTCENTER_WEB_PROVIDER", False),
            productcenter_max_cards=_int("PRODUCTCENTER_MAX_CARDS", 0),
            productcenter_parallel_requests=_int("PRODUCTCENTER_PARALLEL_REQUESTS", 1),
            productcenter_request_interval=_float("PRODUCTCENTER_REQUEST_INTERVAL", 1.0),
            productcenter_connection_retries=_int("PRODUCTCENTER_CONNECTION_RETRIES", 180),
            productcenter_cache_dir=(
                Path(value) if (value := os.getenv("PRODUCTCENTER_CACHE_DIR")) else None
            ),
            use_moscow_suppliers_provider=_bool("MOSCOW_SUPPLIERS_PROVIDER", False),
            moscow_suppliers_export_url=os.getenv("MOSCOW_SUPPLIERS_EXPORT_URL", ""),
            use_supl_biz_provider=_bool("SUPL_BIZ_WEB_PROVIDER", False),
            supl_biz_max_cards=_int("SUPL_BIZ_MAX_CARDS", 0),
        )
