"""Проверка нормализатора на настоящих справочниках репозитория.

Сеть, ClickHouse и исходные CSV не нужны: разбор — чистые функции, а правила
читаются из `backend/reference`. Названия взяты по образцу реальных строк
источников, включая порчу чисел Excel и артикул, приклеенный к названию.
"""

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.repository.reference import load_normalizer_reference
from src.models.catalog.offer import Offer
from src.models.catalog.package import SupplierPackage
from src.models.catalog.source import Source
from src.models.enums import SourceType
from src.service.normalizer import OfferNormalizer
from src.service.normalizer.text import clean, fix_numbers, stem

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def offer(name: str, **fields: object) -> Offer:
    return Offer(
        offer_id=UUID(int=1),
        source_id=UUID(int=2),
        external_id="1",
        url="https://example.test/1",
        name=name,
        first_seen_at=NOW,
        last_seen_at=NOW,
        **fields,
    )


async def normalizer() -> OfferNormalizer:
    reference = await load_normalizer_reference()
    return OfferNormalizer(reference.units, reference.rules)


def check_text_rules() -> None:
    assert clean("Бумага  офисная\t А4 ") == "Бумага офисная А4"
    # Число, испорченное Excel: «1.79» он превращает в дату.
    assert fix_numbers("янв.79", {"янв": "1"}) == "1.79"
    assert fix_numbers("сен.5", {"сен": "9"}) == "9.5"
    # Excel портит и в обратную сторону: «10.6» превращается в «10.июн».
    assert fix_numbers("10.июн", {"июн": "6"}) == "10.6"
    assert fix_numbers("Длина 12.мар м", {"мар": "3"}) == "Длина 12.3 м"
    assert stem("хомуты") == stem("хомут")
    assert stem("футболки") == stem("футболка")
    assert stem("ключ") == "ключ"
    # Короткое слово не теряет смысл: основа не режется до двух букв.
    assert stem("вода") == "вода"


async def check_name_decomposition() -> None:
    service = await normalizer()
    result = service.normalize_offer(
        offer("Комбинированный ключ, 19 мм, CrV, ГОСТ 16983 СИБРТЕХ 14912", brand="СИБРТЕХ")
    )
    normalization = result.normalization
    assert normalization is not None
    assert normalization.article == "14912", normalization
    assert normalization.brand == "СИБРТЕХ", normalization
    assert "сибртех" not in normalization.name, normalization.name
    assert "гост" not in normalization.name.lower(), normalization.name
    assert normalization.attributes["gost"].startswith("ГОСТ"), normalization.attributes
    assert normalization.attributes["length_mm"] == "19", normalization.attributes
    assert "ключ" in normalization.name, normalization.name
    # Ключ склейки у брендового товара строится по бренду и артикулу.
    assert normalization.key == "сибртех 14912", normalization.key


async def check_attributes_and_units() -> None:
    service = await normalizer()
    result = service.normalize_offer(
        offer(
            "Тиски слесарные",
            attributes={"Длина, мм": "189", "Вес, кг": "янв.79", "Единица товара": "Штука"},
            price=Decimal("1200.00"),
        )
    )
    normalization = result.normalization
    assert normalization is not None
    # Разные написания одного свойства приходят к одному ключу.
    assert normalization.attributes["length_mm"] == "189", normalization.attributes
    assert normalization.attributes["weight_kg"] == "1.79", normalization.attributes
    assert normalization.unit_code == "796", normalization
    assert normalization.price_per_unit == Decimal("1200.0000"), normalization
    assert normalization.price_unit_code == "796", normalization


async def check_price_per_base_unit() -> None:
    service = await normalizer()
    per_meter = service.normalize_offer(offer("Кабель", unit="м", price=Decimal("90")))
    assert per_meter.normalization.price_per_unit == Decimal("90.0000")

    # Цена за грамм приводится к килограмму: иначе цены несравнимы.
    per_gram = service.normalize_offer(offer("Припой", unit="г", price=Decimal("2")))
    assert per_gram.normalization.unit_code == "163", per_gram.normalization
    assert per_gram.normalization.price_per_unit == Decimal("2000.0000"), per_gram.normalization
    assert per_gram.normalization.price_unit_code == "166", per_gram.normalization

    # Упаковка с известным количеством даёт цену за штуку.
    pack = service.normalize_offer(
        offer(
            "Бумага офисная",
            unit="упаковка",
            price=Decimal("300"),
            attributes={"Количество в упаковке": "500"},
        )
    )
    assert pack.normalization.price_per_unit == Decimal("0.6000"), pack.normalization
    assert pack.normalization.price_unit_code == "796", pack.normalization


async def check_noise_only_name() -> None:
    service = await normalizer()
    # Такие названия встречаются в каталогах: вся строка — рекламное слово.
    result = service.normalize_offer(offer("ОПТОМ"))
    assert result.normalization.name == "оптом", result.normalization
    assert result.normalization.key == "оптом", result.normalization


async def check_package_keeps_source_values() -> None:
    service = await normalizer()
    source = Source(
        source_id=UUID(int=2),
        name="Фид",
        base_url="https://example.test/",
        source_type=SourceType.FEED,
        provider_name="yml_feed",
    )
    original = offer("Футболка мужская Premium белая", attributes={"Цвет": "белый"})
    package = await service.normalize(SupplierPackage(source=source, offers=(original,)))
    result = package.offers[0]
    # Исходные поля не затираются: нормализация лежит рядом отдельной моделью.
    assert result.name == original.name
    assert result.attributes == {"Цвет": "белый"}
    assert result.normalization.attributes["color"] == "белый"
    assert result.normalization.algorithm_version == service.version


async def check_empty_package() -> None:
    service = await normalizer()
    source = Source(
        source_id=UUID(int=3),
        name="Пустой",
        base_url="https://example.test/",
        source_type=SourceType.DIRECTORY,
        provider_name="empty",
    )
    package = await service.normalize(SupplierPackage(source=source))
    assert package.offers == ()


async def main() -> None:
    check_text_rules()
    await check_name_decomposition()
    await check_attributes_and_units()
    await check_price_per_base_unit()
    await check_noise_only_name()
    await check_package_keeps_source_values()
    await check_empty_package()
    print("Проверка нормализатора пройдена")


if __name__ == "__main__":
    asyncio.run(main())
