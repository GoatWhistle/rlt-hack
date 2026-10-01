"""Перечисления предметной области, повторяющие значения Enum8 в схеме ClickHouse."""

from enum import StrEnum


class SourceType(StrEnum):
    DIRECTORY = "directory"
    WEBSITE = "website"
    FEED = "feed"
    PRICE_LIST = "price_list"
    REGISTRY = "registry"
    DATASET = "dataset"


class VerificationStatus(StrEnum):
    """Подтверждение принадлежности: компании, источника или продавца."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    CONFLICT = "conflict"


class ItemType(StrEnum):
    UNKNOWN = "unknown"
    GOODS = "goods"
    WORK = "work"
    SERVICE = "service"


class Availability(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ON_ORDER = "on_order"


class SupplierRole(StrEnum):
    UNKNOWN = "unknown"
    MANUFACTURER = "manufacturer"
    DISTRIBUTOR = "distributor"
    RESELLER = "reseller"
    SERVICE_PROVIDER = "service_provider"


class ClassificationMethod(StrEnum):
    """Канал, которым получен код ОКПД2: от самого надёжного к запасному."""

    NONE = "none"
    GOLD = "gold"
    REFERENCE = "reference"
    ARCHIVE = "archive"
    SOURCE_MAP = "source_map"
    LEXICON = "lexicon"


class FetchStatus(StrEnum):
    """Итог обхода одного источника."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
