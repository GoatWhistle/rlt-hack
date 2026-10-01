"""Проверка адаптеров источников на фиксированных документах.

Сетевых запросов нет: HTTP-клиент адаптера работает через httpx.MockTransport,
а датасет читается из временного файла. Проверяются разбор фида, карточек
schema.org, каталога компаний и устойчивость к сбою отдельной страницы.
"""

import asyncio
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.supplier import identity
from src.adapter.supplier.aboutpartner_web import AboutPartnerWebProvider
from src.adapter.supplier.errors import SourceUnavailableError
from src.adapter.supplier.inn import is_valid_inn, normalize_inn
from src.adapter.supplier.optkatalog_web import OptKatalogWebProvider
from src.adapter.supplier.schema_org_web import SchemaOrgWebProvider
from src.adapter.supplier.supplier_dataset import SupplierDatasetProvider
from src.adapter.supplier.texzakaz_web import TexZakazWebProvider
from src.adapter.supplier.yml_feed import YmlFeedProvider
from src.models.enums import (
    Availability,
    ItemType,
    SourceType,
    SupplierRole,
    VerificationStatus,
)
from src.models.source import Source
from tests.supplier.fixtures import (
    ABOUTPARTNER_CARD,
    ABOUTPARTNER_SERVICE,
    ABOUTPARTNER_SITEMAP,
    FEED_FULL,
    FEED_WITHOUT_A3,
    OPTKATALOG_CARD,
    OPTKATALOG_CARD_INLINE,
    OPTKATALOG_SITEMAP,
    PRODUCT_PAGE,
    SITEMAP_GOODS,
    SITEMAP_INDEX,
    SUPPLIERS_CSV,
    TEXZAKAZ_CARD,
    TEXZAKAZ_SITEMAP,
)

SHOP_INN = "7804428656"


def transport(pages: dict[str, str], failing: tuple[str, ...] = ()) -> httpx.MockTransport:
    """Отдаёт подготовленные страницы; перечисленные адреса возвращают 500."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url in failing:
            return httpx.Response(500, text="сбой источника")
        body = pages.get(url)
        if body is None:
            return httpx.Response(404, text="нет страницы")
        return httpx.Response(200, text=body, headers={"Content-Type": "text/html; charset=utf-8"})

    return httpx.MockTransport(handler)


def source(name: str, base_url: str, source_type: SourceType, provider: str, **extra) -> Source:
    return Source(
        source_id=identity.source_id(base_url, provider),
        name=name,
        base_url=base_url,
        source_type=source_type,
        provider_name=provider,
        **extra,
    )


async def check_yml_feed() -> None:
    feed_url = "https://shop.test/feed.xml"
    feed_source = source(
        "Канцторг",
        "https://shop.test/",
        SourceType.FEED,
        "yml_feed",
        ownership_status=VerificationStatus.VERIFIED,
        ownership_evidence_url="https://shop.test/about",
    )
    provider = YmlFeedProvider(
        feed_source,
        feed_url=feed_url,
        supplier_inn=SHOP_INN,
        delivery_regions=("Санкт-Петербург",),
        transport=transport({feed_url: FEED_FULL}),
    )
    package = await provider.fetch()
    assert package.source is feed_source
    assert len(package.suppliers) == 1, package.suppliers
    supplier = package.suppliers[0]
    assert supplier.name == "ООО «Канцторг»"
    assert supplier.inn == SHOP_INN
    assert supplier.identity_status == VerificationStatus.VERIFIED
    assert len(package.offers) == 2, package.offers
    paper = next(offer for offer in package.offers if offer.external_id == "A-1")
    assert paper.name == "Бумага А4 500 листов"
    assert paper.price == Decimal("350.50")
    assert paper.currency == "RUR"
    assert paper.item_type == ItemType.GOODS
    assert paper.availability == Availability.AVAILABLE
    assert paper.attributes["Плотность"] == "80 г/м2"
    assert paper.source_category == "Бумага"
    assert paper.delivery_regions == ("Санкт-Петербург",)
    assert paper.supplier_id == supplier.supplier_id
    assert paper.seller_status == VerificationStatus.VERIFIED
    a3 = next(offer for offer in package.offers if offer.external_id == "A-2")
    # available="false" в YML означает поставку под заказ, а не отсутствие.
    assert a3.availability == Availability.ON_ORDER

    # Изменилась только цена: ID и хеш смысловых полей остаются прежними.
    repeated = await YmlFeedProvider(
        feed_source,
        feed_url=feed_url,
        supplier_inn=SHOP_INN,
        transport=transport({feed_url: FEED_WITHOUT_A3}),
    ).fetch()
    assert len(repeated.offers) == 1, repeated.offers
    same = repeated.offers[0]
    assert same.offer_id == paper.offer_id
    assert same.content_hash == paper.content_hash
    assert same.price == Decimal("399.00")

    # Недоступный фид — провал обхода: пакета нет.
    failed = YmlFeedProvider(
        feed_source, feed_url=feed_url, transport=transport({}, failing=(feed_url,))
    )
    try:
        await failed.fetch()
    except SourceUnavailableError:
        pass
    else:
        raise AssertionError("недоступный фид должен поднимать ошибку источника")


async def check_supplier_dataset() -> None:
    with tempfile.TemporaryDirectory(prefix="rlt-dataset-") as temporary:
        path = Path(temporary) / "Поставщики_24-25.csv"
        path.write_text(SUPPLIERS_CSV, encoding="utf-8")
        dataset_source = source(
            "Поставщики из задания",
            path.as_uri(),
            SourceType.DATASET,
            "supplier_dataset",
        )
        provider = SupplierDatasetProvider(dataset_source, path, region="Санкт-Петербург")
        package = await provider.fetch()
        assert not package.offers, "в датасете нет ассортимента"
        inns = sorted(supplier.inn or "" for supplier in package.suppliers)
        # Повторы по ИНН свёрнуты, строка с нулевым ИНН отброшена.
        assert inns == ["636200108061", "7707049388", "7804428656"], inns
        assert all(item.region == "Санкт-Петербург" for item in package.suppliers)
        assert all(
            item.identity_status == VerificationStatus.UNVERIFIED for item in package.suppliers
        )
        assert all(
            item.identity_evidence_url == path.resolve().as_uri() for item in package.suppliers
        )

        missing = SupplierDatasetProvider(dataset_source, Path(temporary) / "нет.csv")
        try:
            await missing.fetch()
        except SourceUnavailableError:
            pass
        else:
            raise AssertionError("отсутствующий файл должен поднимать ошибку источника")


async def check_schema_org_site() -> None:
    site_source = source(
        "Канцторг",
        "https://kanctorg.test/",
        SourceType.WEBSITE,
        "schema_org_web",
    )
    pages = {
        "https://kanctorg.test/sitemap.xml": SITEMAP_INDEX,
        "https://kanctorg.test/sitemap-goods.xml": SITEMAP_GOODS,
        "https://kanctorg.test/product/paper-a4": PRODUCT_PAGE,
    }
    provider = SchemaOrgWebProvider(
        site_source,
        # Страница /about отдаёт 500: обход остальных адресов не отменяется.
        transport=transport(pages, failing=("https://kanctorg.test/about",)),
    )
    package = await provider.fetch()
    assert len(package.offers) == 1, package.offers
    offer = package.offers[0]
    assert offer.name == "Бумага А4 500 листов"
    assert offer.article == "SV-500"
    assert offer.brand == "Светокопи"
    assert offer.price == Decimal("350.50")
    assert offer.currency == "RUB"
    assert offer.availability == Availability.AVAILABLE
    assert offer.attributes["Плотность"] == "80 г/м2"
    assert offer.url == "https://kanctorg.test/product/paper-a4"
    supplier = package.suppliers[0]
    # Реквизиты взяты из текста страницы, а не из названия сайта.
    assert supplier.inn == SHOP_INN
    assert offer.supplier_id == supplier.supplier_id

    empty = SchemaOrgWebProvider(
        site_source,
        transport=transport({"https://kanctorg.test/sitemap.xml": SITEMAP_INDEX}),
    )
    try:
        await empty.fetch()
    except SourceUnavailableError:
        pass
    else:
        raise AssertionError("пустой sitemap должен поднимать ошибку источника")


async def check_optkatalog_directory() -> None:
    directory_source = source(
        "ОптКаталог",
        "https://optkatalog.ru/",
        SourceType.DIRECTORY,
        "optkatalog_web",
    )
    pages = {
        "https://optkatalog.ru/sitemap.xml": OPTKATALOG_SITEMAP,
        "https://optkatalog.ru/postavschiki/bumaga/ofisnaya/kanctorg/": OPTKATALOG_CARD,
        "https://optkatalog.ru/postavschiki/bumaga/ofisnaya/papirus/": OPTKATALOG_CARD_INLINE,
    }
    package = await OptKatalogWebProvider(directory_source, transport=transport(pages)).fetch()
    assert len(package.suppliers) == 2, package.suppliers
    kanctorg = next(item for item in package.suppliers if item.inn == SHOP_INN)
    assert kanctorg.name == "ООО «Канцторг»"
    # Разделы каталога карточками не считаются: обходятся только листья дерева.
    assert kanctorg.identity_evidence_url.endswith("/kanctorg/")
    assert kanctorg.region == "Ленинградская обл."
    assert kanctorg.website == "https://kanctorg.test/"
    assert kanctorg.contacts["legal_name"] == 'ООО "Канцторг"'
    assert kanctorg.contacts["founded"] == "2001"
    assert kanctorg.contacts["email"] == "sales@kanctorg.test"
    assert kanctorg.identity_status == VerificationStatus.UNVERIFIED
    goods = sorted(
        offer.name for offer in package.offers if offer.supplier_id == kanctorg.supplier_id
    )
    assert goods == ["Бумага А4 500 листов", "Ручка шариковая"], goods

    # Реквизиты строкой «Метка: значение» читаются так же, как заголовком блока.
    papirus = next(item for item in package.suppliers if item.inn == "7707049388")
    assert papirus.contacts["founded"] == "1996"
    papirus_goods = [offer for offer in package.offers if offer.supplier_id == papirus.supplier_id]
    # Длинный абзац описывает компанию, а не позицию номенклатуры.
    assert [offer.name for offer in papirus_goods] == ["Картон переплётный"], papirus_goods
    # Типов в свойстве несколько: роль выбирается по порядку значимости.
    assert papirus_goods[0].supplier_role == SupplierRole.DISTRIBUTOR
    assert papirus_goods[0].role_evidence_text == "Дистрибьютор, Оптовый поставщик"

    # Сбой одной карточки не отменяет остальные компании.
    partial = OptKatalogWebProvider(
        directory_source,
        transport=transport(
            pages, failing=("https://optkatalog.ru/postavschiki/bumaga/ofisnaya/papirus/",)
        ),
    )
    package = await partial.fetch()
    assert [item.inn for item in package.suppliers] == [SHOP_INN], package.suppliers

    # Sitemap без карточек компаний — провал обхода.
    broken = OptKatalogWebProvider(
        directory_source,
        transport=transport({"https://optkatalog.ru/sitemap.xml": SITEMAP_GOODS}),
    )
    try:
        await broken.fetch()
    except SourceUnavailableError:
        pass
    else:
        raise AssertionError("каталог без карточек должен поднимать ошибку источника")


async def check_aboutpartner_directory() -> None:
    directory_source = source(
        "О Партнёре",
        "https://aboutpartner.ru/",
        SourceType.DIRECTORY,
        "aboutpartner_web",
    )
    pages = {
        "https://aboutpartner.ru/sitemap-producers.xml": ABOUTPARTNER_SITEMAP,
        "https://aboutpartner.ru/producer/pc-producer-1": ABOUTPARTNER_CARD,
        "https://aboutpartner.ru/producer/crmindex-servicespbx": ABOUTPARTNER_SERVICE,
    }
    package = await AboutPartnerWebProvider(directory_source, transport=transport(pages)).fetch()
    # Карточка сервиса размечена без Organization: компании из неё не берутся.
    assert len(package.suppliers) == 1, package.suppliers
    supplier = package.suppliers[0]
    assert supplier.inn == SHOP_INN
    assert supplier.region == "Ленинградская область"
    # Профиль в соцсети сайтом компании не считается.
    assert supplier.website == "https://kanctorg.test"
    assert supplier.contacts["phone"] == "+7 (812) 000-00-00"
    assert len(package.offers) == 2, package.offers
    paper = next(offer for offer in package.offers if offer.name == "Бумага А4 500 листов")
    assert paper.url == "https://aboutpartner.ru/product/pc-product-1"
    assert paper.brand == "Светокопи"
    assert paper.item_type == ItemType.GOODS
    assert paper.supplier_role == SupplierRole.MANUFACTURER
    assert paper.supplier_id == supplier.supplier_id

    # Карточки сервисов идут в sitemap первыми, но короткий обход берёт компанию.
    short = AboutPartnerWebProvider(directory_source, max_companies=1, transport=transport(pages))
    package = await short.fetch()
    assert [item.inn for item in package.suppliers] == [SHOP_INN], package.suppliers

    broken = AboutPartnerWebProvider(
        directory_source,
        transport=transport({"https://aboutpartner.ru/sitemap-producers.xml": SITEMAP_GOODS}),
    )
    try:
        await broken.fetch()
    except SourceUnavailableError:
        pass
    else:
        raise AssertionError("каталог без карточек должен поднимать ошибку источника")


async def check_texzakaz_directory() -> None:
    directory_source = source(
        "ТехЗаказ",
        "https://texzakaz.ru/",
        SourceType.DIRECTORY,
        "texzakaz_web",
    )
    pages = {
        "https://texzakaz.ru/sitemap.xml": TEXZAKAZ_SITEMAP,
        "https://texzakaz.ru/p/10": TEXZAKAZ_CARD,
    }
    package = await TexZakazWebProvider(directory_source, transport=transport(pages)).fetch()
    assert len(package.suppliers) == 1, package.suppliers
    supplier = package.suppliers[0]
    assert supplier.name == "Канцторг"
    assert supplier.inn == SHOP_INN
    assert supplier.region == "Ленинградская область"
    assert supplier.contacts["locality"] == "Всеволожск"
    assert supplier.identity_evidence_url == "https://texzakaz.ru/p/10"
    names = sorted(offer.name for offer in package.offers)
    assert names == ["Бумага А4 500 листов", "Ручка шариковая"], names
    assert all(offer.supplier_role == SupplierRole.MANUFACTURER for offer in package.offers)
    assert all(offer.supplier_id == supplier.supplier_id for offer in package.offers)

    # Повторный обход тех же данных даёт те же идентификаторы и хеши.
    repeated = await TexZakazWebProvider(directory_source, transport=transport(pages)).fetch()
    assert sorted(offer.offer_id for offer in repeated.offers) == sorted(
        offer.offer_id for offer in package.offers
    )
    assert sorted(offer.content_hash for offer in repeated.offers) == sorted(
        offer.content_hash for offer in package.offers
    )

    broken = TexZakazWebProvider(
        directory_source, transport=transport({"https://texzakaz.ru/sitemap.xml": SITEMAP_GOODS})
    )
    try:
        await broken.fetch()
    except SourceUnavailableError:
        pass
    else:
        raise AssertionError("каталог без карточек должен поднимать ошибку источника")


async def main() -> None:
    assert is_valid_inn(SHOP_INN) and is_valid_inn("636200108061")
    assert normalize_inn("0000000000") is None
    assert normalize_inn("не ИНН") is None
    await check_yml_feed()
    await check_supplier_dataset()
    await check_schema_org_site()
    await check_optkatalog_directory()
    await check_aboutpartner_directory()
    await check_texzakaz_directory()
    print("Проверка адаптеров источников пройдена")


if __name__ == "__main__":
    asyncio.run(main())
