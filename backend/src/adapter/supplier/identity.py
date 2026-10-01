"""Устойчивые идентификаторы и хеши содержимого.

Правила идентичности общие для всех адаптеров: повторный обход обновляет ту же
сущность, а не создаёт запись по названию. Название идентификатором не является.
"""

import hashlib
import json
from collections.abc import Mapping
from uuid import NAMESPACE_URL, UUID, uuid5

# Пространство имён проекта: фиксировано, иначе ID перестанут совпадать.
NAMESPACE = uuid5(NAMESPACE_URL, "https://rlt-hack/supplier-search")


def _uuid(kind: str, *parts: str) -> UUID:
    return uuid5(NAMESPACE, kind + ":" + "|".join(parts))


def source_id(base_url: str, provider_name: str) -> UUID:
    return _uuid("source", base_url.strip().rstrip("/").lower(), provider_name)


def supplier_id(inn: str | None, source: UUID, key: str) -> UUID:
    """ИНН — основной ключ компании; без него ID привязан к источнику.

    Записи без ИНН объединяются с подтверждёнными компаниями только после
    проверки реквизитов: автоматического слияния по названию нет.
    """
    if inn:
        return _uuid("supplier", "inn", inn.strip())
    return _uuid("supplier", "source", str(source), key)


def offer_id(source: UUID, external_id: str) -> UUID:
    """Идентичность предложения — источник и внешний ID продавца или URL варианта."""
    return _uuid("offer", str(source), external_id.strip())


def offer_content_hash(
    name: str,
    description: str = "",
    item_type: str = "",
    brand: str = "",
    article: str = "",
    unit: str = "",
    okpd2_code: str = "",
    attributes: Mapping[str, str] | None = None,
) -> str:
    """Хеш смысловых полей предложения.

    Цена и доступность в хеш не входят: их изменение не обязано отменять
    выполненное сопоставление с позицией каталога.
    """
    payload = {
        "name": " ".join(name.split()).casefold(),
        "description": " ".join(description.split()).casefold(),
        "item_type": item_type,
        "brand": brand.casefold(),
        "article": article.casefold(),
        "unit": unit.casefold(),
        "okpd2_code": okpd2_code,
        "attributes": {
            key.casefold(): " ".join(value.split()).casefold()
            for key, value in sorted((attributes or {}).items())
        },
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
