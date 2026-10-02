from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, WithJsonSchema
from pydantic.alias_generators import to_camel


def rfc3339(value: datetime) -> str:
    moment = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return moment.isoformat().replace("+00:00", "Z")


def plain_decimal(value: Decimal) -> str:
    return format(value, "f")


def score(value: float) -> float:
    return round(value, 4)


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(rfc3339, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "format": "date-time"}),
]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
