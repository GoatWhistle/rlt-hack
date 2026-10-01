"""Устойчивые идентификаторы и хеши содержимого.

Правила идентичности общие для всех адаптеров: повторный обход обновляет ту же
сущность, а не создаёт запись по названию. Название идентификатором не является.
"""

import hashlib
import json
import re
from collections.abc import Mapping
from uuid import NAMESPACE_URL, UUID, uuid5

# Пространство имён проекта: фиксировано, иначе ID перестанут совпадать.
NAMESPACE = uuid5(NAMESPACE_URL, "https://rlt-hack/supplier-search")

# Ключ предложения внутри источника. Длинный ключ ничего не улучшает: от него
# берётся UUID, а читают его только при разборе расхождений.
EXTERNAL_ID_MAX = 200
FINGERPRINT_LENGTH = 12
_PUNCTUATION = re.compile(r"[^0-9a-zа-яё]+")


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


def name_fingerprint(name: str) -> str:
    """Короткий отпечаток названия для страниц со списком товаров.

    Правило заморожено навсегда и намеренно не использует нормализатор: смена
    его правил не должна менять идентичность предложений. Регистр, пунктуация
    и лишние пробелы отпечаток не меняют, поэтому косметическая правка в
    каталоге не превращает позицию в новую.
    """
    key = _PUNCTUATION.sub(" ", name.casefold().replace("ё", "е")).strip()
    key = " ".join(key.split())
    return hashlib.sha1(key.encode()).hexdigest()[:FINGERPRINT_LENGTH]


def external_id(source_key: str = "", url: str = "", name: str = "") -> str:
    """Ключ предложения внутри источника по единому правилу для всех адаптеров.

    Порядок: собственный идентификатор источника (артикул, `id` фида,
    `productID`), затем адрес страницы, и только если на одной странице
    перечислено несколько позиций — адрес с отпечатком названия. Само название
    в ключ не попадает: оно меняется чаще, чем предмет.
    """
    own = source_key.strip()
    if own:
        return own[:EXTERNAL_ID_MAX]
    address = url.strip()
    if not address:
        raise ValueError("ключ предложения нельзя построить без адреса и идентификатора")
    if not name.strip():
        return address[:EXTERNAL_ID_MAX]
    return f"{address[:EXTERNAL_ID_MAX]}#{name_fingerprint(name)}"


def rekey(previous: str, url: str, name: str) -> str:
    """Переводит ранее сохранённый ключ на действующее правило.

    Ключ, который источник выдал сам, остаётся как есть: он и был правильным.
    Ключи, собранные из адреса и названия, пересчитываются в отпечаток.
    """
    address = url.strip()
    if previous and address and not previous.startswith(address):
        return previous[:EXTERNAL_ID_MAX]
    if previous == address:
        return external_id(url=address)
    return external_id(url=address, name=name)


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
