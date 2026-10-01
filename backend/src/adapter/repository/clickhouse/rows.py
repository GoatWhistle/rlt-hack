"""Преобразование значений ClickHouse в типы моделей."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID


def to_uuid(value: object) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def to_optional_uuid(value: object) -> UUID | None:
    return None if value is None or value == "" else to_uuid(value)


def to_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value)).replace(tzinfo=UTC)


def to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))
