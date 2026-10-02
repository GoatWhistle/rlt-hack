"""Проверка классификатора и справочников таксономии.

Сеть и ClickHouse не нужны: архив подменён заглушкой, остальное читается из
`backend/reference`. Проверяются все каналы, отказ от ответа, проекция рубрики и
согласованность самих справочников.
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.repository.reference import (
    load_classifier_reference,
    load_normalizer_reference,
)
from src.models.catalog.offer import Offer
from src.models.catalog.package import SupplierPackage
from src.models.catalog.source import Source
from src.models.enums import ClassificationMethod, ItemType, SourceType
from src.service.classifier import OfferClassifier
from src.service.classifier.taxonomy import level_of, normalize_code, rubric_of
from src.service.normalizer import OfferNormalizer

NOW = datetime(2026, 10, 1, tzinfo=UTC)


class FakeArchive:
    """Архив закупок: пары «название — код», как в таблице ТРУ."""

    def __init__(self, items: list[tuple[str, str]]) -> None:
        self.items = items
        self.calls = 0

    async def load_items(self, limit: int) -> list[tuple[str, str]]:
        self.calls += 1
        return self.items[:limit]


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


def source(provider_name: str) -> Source:
    return Source(
        source_id=UUID(int=2),
        name=provider_name,
        base_url="https://example.test/",
        source_type=SourceType.FEED,
        provider_name=provider_name,
    )


async def build(archive: FakeArchive | None = None) -> tuple[OfferNormalizer, OfferClassifier]:
    normalizer_reference = await load_normalizer_reference()
    normalizer = OfferNormalizer(normalizer_reference.units, normalizer_reference.rules)
    reference = await load_classifier_reference(normalizer.name_key, normalizer.name_stems)
    classifier = OfferClassifier(
        okpd2=reference.okpd2,
        rubrics=reference.rubrics,
        lexicon=reference.lexicon,
        categories=reference.categories,
        archive=archive,
        name_key=normalizer.name_key,
    )
    return normalizer, classifier


async def run(
    classifier: OfferClassifier, normalizer: OfferNormalizer, provider: str, *offers: Offer
):
    package = SupplierPackage(source=source(provider), offers=offers)
    package = await normalizer.normalize(package)
    return (await classifier.classify(package)).offers


def check_taxonomy_rules() -> None:
    assert normalize_code("25.73") == "25.73"
    assert normalize_code("17.12.14.129") == "17.12.14.129"
    assert normalize_code("не код") == ""
    assert level_of("25") == 2
    assert level_of("17.12.14.129") == 9
    prefixes = {"25": "metalware", "25.73": "tools"}
    # Выигрывает самый длинный совпавший префикс, а не первый попавшийся.
    assert rubric_of("25.73.30", prefixes) == "tools"
    assert rubric_of("25.94", prefixes) == "metalware"
    assert rubric_of("28.13", prefixes) == ""


async def check_channels_order() -> None:
    normalizer, classifier = await build(FakeArchive([("Крахмал картофельный", "10.62.11.111")]))
    gold, archive, category, lexicon, unknown = await run(
        classifier,
        normalizer,
        "yml_feed",
        offer("Бумага офисная", okpd2_code="17.12.14.129"),
        offer("Крахмал картофельный"),
        offer("Стальной кронштейн 150х200 мм", source_category="Кронштейны"),
        offer("Реверсивная отвертка Т-образная"),
        offer("Изделие без узнаваемого названия ЩЩЩ"),
    )

    assert gold.classification.method is ClassificationMethod.GOLD, gold.classification
    assert gold.classification.okpd2_code == "17.12.14.129"
    assert gold.classification.okpd2_level == 9
    assert gold.classification.rubric_code == "office", gold.classification

    assert archive.classification.method is ClassificationMethod.ARCHIVE, archive.classification
    assert archive.classification.okpd2_code == "10.62.11.111"
    assert archive.classification.rubric_code == "food", archive.classification

    assert category.classification.method is ClassificationMethod.SOURCE_MAP, (
        category.classification
    )
    assert category.classification.okpd2_code == "25.99"

    assert lexicon.classification.method is ClassificationMethod.LEXICON, lexicon.classification
    assert lexicon.classification.okpd2_code == "25.73"
    assert "отверт" in lexicon.classification.evidence, lexicon.classification

    # Не сработал ни один канал — кода нет, и это видно по методу.
    assert unknown.classification.method is ClassificationMethod.NONE, unknown.classification
    assert unknown.classification.okpd2_code == ""
    assert unknown.okpd2_code == ""


async def check_reference_channel() -> None:
    normalizer, classifier = await build()
    (result,) = await run(classifier, normalizer, "yml_feed", offer("Цемент"))
    assert result.classification.method is ClassificationMethod.REFERENCE, result.classification
    assert result.classification.okpd2_code == "23.51", result.classification


async def check_head_word_wins() -> None:
    normalizer, classifier = await build()
    # В «сверле по стеклу» предмет — сверло: выигрывает слово, стоящее раньше.
    (result,) = await run(
        classifier, normalizer, "yml_feed", offer("Сверло по стеклу и керамической плитке")
    )
    assert result.classification.okpd2_code == "25.73", result.classification


async def check_item_type() -> None:
    normalizer, classifier = await build()
    goods, service_item, work, middle = await run(
        classifier,
        normalizer,
        "yml_feed",
        offer("Футболка мужская"),
        offer("Оказание услуг по организации горячего питания"),
        offer("Выполнение работ по строительству подстанции"),
        offer("Пистолет для монтажной пены"),
    )
    assert goods.item_type is ItemType.GOODS, goods.classification
    assert service_item.classification.item_type is ItemType.SERVICE, service_item.classification
    assert work.classification.item_type is ItemType.WORK, work.classification
    # Оборот в середине названия о типе ничего не говорит: это товар, не работы.
    assert middle.classification.item_type is not ItemType.WORK, middle.classification


async def check_archive_index_once_and_conflicts() -> None:
    archive = FakeArchive(
        [
            ("Крахмал картофельный", "10.62.11.111"),
            ("Спорная позиция", "10.11.11.111"),
            ("Спорная позиция", "25.73.30.000"),
        ]
    )
    normalizer, classifier = await build(archive)
    first, conflicting = await run(
        classifier,
        normalizer,
        "yml_feed",
        offer("Крахмал картофельный"),
        offer("Спорная позиция"),
    )
    assert first.classification.method is ClassificationMethod.ARCHIVE
    # Одно название с двумя кодами — лучше не дать кода, чем дать неверный.
    assert conflicting.classification.okpd2_code == "", conflicting.classification

    await run(classifier, normalizer, "yml_feed", offer("Крахмал картофельный"))
    assert archive.calls == 1, archive.calls


async def check_reference_is_consistent() -> None:
    normalizer_reference = await load_normalizer_reference()
    normalizer = OfferNormalizer(normalizer_reference.units, normalizer_reference.rules)
    reference = await load_classifier_reference(normalizer.name_key, normalizer.name_stems)
    classes = reference.okpd2.classes()
    assert len(classes) > 80, len(classes)
    for code in classes:
        assert rubric_of(code, reference.rubrics.prefixes), f"класс {code} без рубрики"
        assert code in reference.rubrics.class_types, f"класс {code} без типа позиции"
    for _, code in reference.lexicon.entries:
        assert normalize_code(code) == code, f"словарь: неверный код {code}"
        assert reference.okpd2.has_class(code), f"словарь: неизвестный класс {code}"
    for rubric in reference.rubrics.names:
        assert rubric in set(reference.rubrics.prefixes.values()), f"рубрика {rubric} без префиксов"


async def main() -> None:
    check_taxonomy_rules()
    await check_channels_order()
    await check_reference_channel()
    await check_head_word_wins()
    await check_item_type()
    await check_archive_index_once_and_conflicts()
    await check_reference_is_consistent()
    print("Проверка классификатора пройдена")


if __name__ == "__main__":
    asyncio.run(main())
