"""Проверка правил идентичности предложения.

Ключ источника определяет offer_id, а на нём висит вся история позиции,
поэтому правило проверяется отдельно: оно должно переживать косметические
правки названия и не зависеть от нормализатора.
"""

import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.supplier import identity

SOURCE = UUID(int=5)
URL = "https://texzakaz.ru/p/252"


def check_priority() -> None:
    # Свой идентификатор источника надёжнее адреса.
    assert identity.external_id(source_key="4613", url=URL, name="Товар") == "4613"
    # Одна позиция на странице — ключом служит адрес.
    assert identity.external_id(url=URL) == URL
    # Несколько позиций на странице — адрес с отпечатком названия.
    composite = identity.external_id(url=URL, name="Прокладка под рельс Р-50")
    assert composite.startswith(f"{URL}#"), composite
    assert len(composite) == len(URL) + 1 + identity.FINGERPRINT_LENGTH, composite


def check_cosmetic_edits_keep_identity() -> None:
    first = identity.external_id(url=URL, name="Прокладка под рельс Р-50")
    for variant in (
        "прокладка под рельс р-50",
        "Прокладка  под  рельс, Р-50",
        "Прокладка под рельс Р-50!",
        "Прокладка под рельс Р-50 ",
    ):
        assert identity.external_id(url=URL, name=variant) == first, variant
    # Другой предмет — другой ключ.
    assert identity.external_id(url=URL, name="Прокладка под рельс Р-65") != first


def check_length_limit() -> None:
    long_url = "https://optkatalog.ru/" + "a" * 500
    key = identity.external_id(url=long_url, name="Очень длинное название позиции")
    assert len(key) <= identity.EXTERNAL_ID_MAX + 1 + identity.FINGERPRINT_LENGTH, len(key)
    assert identity.external_id(source_key="x" * 500) == "x" * identity.EXTERNAL_ID_MAX


def check_rekey() -> None:
    # Ключ, выданный источником, остаётся прежним: он и был правильным.
    assert identity.rekey("4613", "https://shop.test/p/1", "Товар") == "4613"
    # Адрес как ключ остаётся адресом.
    assert identity.rekey(URL, URL, "Товар") == URL
    # Старый ключ из адреса и названия переходит в отпечаток.
    old = f"{URL}#Прокладка под рельс Р-50"
    new = identity.rekey(old, URL, "Прокладка под рельс Р-50")
    assert new == identity.external_id(url=URL, name="Прокладка под рельс Р-50"), new
    assert new != old
    # Повторный перевод ничего не меняет.
    assert identity.rekey(new, URL, "Прокладка под рельс Р-50") == new


def check_offer_id_follows_key() -> None:
    first = identity.offer_id(SOURCE, "4613")
    assert first == identity.offer_id(SOURCE, " 4613 "), "пробелы не меняют идентичность"
    assert first != identity.offer_id(UUID(int=6), "4613"), "ключ уникален внутри источника"
    assert first != identity.offer_id(SOURCE, "4614")


def check_empty_key_refused() -> None:
    try:
        identity.external_id()
    except ValueError:
        return
    raise AssertionError("ключ без адреса и идентификатора должен отвергаться")


def main() -> None:
    check_priority()
    check_cosmetic_edits_keep_identity()
    check_length_limit()
    check_rekey()
    check_offer_id_follows_key()
    check_empty_key_refused()
    print("Проверка правил идентичности пройдена")


if __name__ == "__main__":
    main()
