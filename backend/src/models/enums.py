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


class Locale(StrEnum):
    RU = "ru"
    EN = "en"


class CandidateStatus(StrEnum):
    RECOMMENDED = "recommended"
    CHECK = "check"


class MatchBasis(StrEnum):
    STOCK = "stock"
    CATALOG = "catalog"
    INFERRED = "inferred"


class CheckReason(StrEnum):
    INN_MISSING = "innMissing"
    IDENTITY_CONFLICT = "identityConflict"
    ROLE_UNCONFIRMED = "roleUnconfirmed"
    NO_CURRENT_OFFER = "noCurrentOffer"
    RANGE_UNCONFIRMED = "rangeUnconfirmed"
    SOURCE_UNAVAILABLE = "sourceUnavailable"


class EvidenceKind(StrEnum):
    CATALOG = "catalog"
    PRICE = "price"
    PURCHASE = "purchase"
    REGISTRY = "registry"


class ItemOrigin(StrEnum):
    TEXT = "text"
    INFERRED = "inferred"
    USER = "user"


class CompanyRole(StrEnum):
    MANUFACTURER = "manufacturer"
    DISTRIBUTOR = "distributor"
    SUPPLIER = "supplier"
    SUPPLIER_DISTRIBUTOR = "supplierDistributor"
    SERVICE_PROVIDER = "serviceProvider"
    UNKNOWN = "unknown"


class PurchaseOutcome(StrEnum):
    WINNER = "winner"
    PARTICIPANT = "participant"


class MatchStatus(StrEnum):
    UNMATCHED = "unmatched"
    REVIEW = "review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class HighlightCode(StrEnum):
    SAME_REGION = "sameRegion"
    COVERS_ITEMS = "coversItems"
    IN_STOCK = "inStock"
    HAS_PRICE = "hasPrice"
    PAST_WINS = "pastWins"
    SIMILAR_PURCHASES = "similarPurchases"
    VERIFIED_IDENTITY = "verifiedIdentity"


class WarningCode(StrEnum):
    CHANNEL_FAILED = "channelFailed"
    ENRICHMENT_FAILED = "enrichmentFailed"
    ARCHIVE_FAILED = "archiveFailed"
    ITEMS_INFERRED = "itemsInferred"
    ITEMS_TRUNCATED = "itemsTruncated"


class RetrievalChannel(StrEnum):
    LEXICAL = "lexical"
    HISTORY = "history"
    SEMANTIC = "semantic"
    CATALOG_VECTOR = "catalogVector"


class SearchStage(StrEnum):
    PARSE = "parse"
    CHANNELS = "channels"
    ENRICH = "enrich"
    POLICY = "policy"
    ARCHIVE = "archive"


class EnrichmentSource(StrEnum):
    DIRECTORY = "directory"
    OFFERS = "offers"
    CURRENT_OFFERS = "currentOffers"
    HISTORY = "history"


class ComponentState(StrEnum):
    UP = "up"
    DOWN = "down"


class IssueCode(StrEnum):
    MISSING_LOT_ID = "missingLotId"
    BAD_LOT_ID = "badLotId"
    DUPLICATE_LOT = "duplicateLot"
    MISSING_TITLE = "missingTitle"
    BAD_PRICE = "badPrice"
    BAD_DATE = "badDate"
    COLUMN_COUNT = "columnCount"


class LotStatus(StrEnum):
    QUEUED = "queued"
    READY = "ready"
    NEEDS_CHECK = "needsCheck"
    NO_CANDIDATES = "noCandidates"
    FAILED = "failed"
