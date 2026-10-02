"""Проверка равномерной выборки Supl.biz по категориям на искусственных страницах.

Запуск из каталога `backend`:
`uv run --no-project --python 3.13 --with httpx python tests/supplier/supl_biz_balanced_smoke.py`.
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.supl_biz_web import PROVIDER_NAME, SuplBizWebProvider
from src.models.catalog.source import Source
from src.models.enums import SourceType
from tests.supplier.supl_biz_smoke import card, expect

TREE = "https://supl.biz/proposals/"


def script(state: dict) -> str:
    body = json.dumps(state, ensure_ascii=False)
    tag = f'<script id="preloadedState" type="application/json">{body}</script>'
    return f"<html><body>{tag}</body></html>"


def child(category_id: int) -> dict:
    return {"id": category_id, "slug": f"sub{category_id}", "name": f"Подкатегория {category_id}"}


def tree(*roots: tuple[int, list[int], bool]) -> str:
    nodes = [
        {
            "id": root_id,
            "name": f"Категория {root_id}",
            "forAdult": adult,
            "children": [child(number) for number in children],
        }
        for root_id, children, adult in roots
    ]
    return script({"shared": {"category": {"data": nodes}}})


def listing(*ids: int, spam: tuple[int, ...] = ()) -> str:
    hits = [{"id": number, "slug": f"tovar-{number}", "categories": [1]} for number in ids]
    hits += [
        {"id": number, "slug": f"tovar-{number}", "categories": list(range(40))} for number in spam
    ]
    return script({"catalog": {"proposals": {"proposals": {"data": {"hits": hits}}}}})


def url(category_id: int) -> str:
    return f"https://supl.biz/sub{category_id}-category{category_id}/"


def product(number: int) -> str:
    return f"https://supl.biz/tovar-{number}-p{number}/"


def pages() -> dict[str, str]:
    documents = {
        TREE: tree((1, [11, 12], False), (2, [21, 22, 23], False), (3, [31], True)),
        url(11): listing(1, 2, 3, 4, 5, 6),
        url(12): listing(7, 8, 9, spam=(90, 91)),
        url(21): listing(21, 22, 23, 24),
        url(22): listing(1, 25, 26),
        url(23): listing(),
        url(31): listing(31),
    }
    for number in (1, 2, 3, 4, 5, 6, 7, 8, 9, 21, 22, 23, 24, 25, 26):
        documents[product(number)] = card(number, number % 3 + 1, f"Товар {number}", "10", None)
    return documents


def make(documents: dict[str, str]) -> SuplBizWebProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        body = documents.get(str(request.url))
        if body is None:
            return httpx.Response(404, text="нет страницы")
        return httpx.Response(200, text=body)

    source = Source(
        source_id=identity.source_id("https://supl.biz/", PROVIDER_NAME),
        name="Supl.biz",
        base_url="https://supl.biz/",
        source_type=SourceType.DIRECTORY,
        provider_name=PROVIDER_NAME,
    )
    return SuplBizWebProvider(source, retries=0, transport=httpx.MockTransport(handler))


async def check_distribution() -> None:
    sample = await make(pages()).balanced_sample(4)
    names = [share.name for share in sample.shares]
    assert names == ["Категория 1", "Категория 2"], "категория для взрослых пропущена"
    first, second = sample.shares
    assert first.listed == second.listed == 4 and first.fetched == second.fetched == 4
    external = {offer.external_id for offer in sample.package.offers}
    assert {"1", "7", "2", "8"} <= external, "категория 1 берёт по кругу из обеих подкатегорий"
    assert len(sample.package.offers) == 8
    assert "31" not in external
    assert not {"90", "91"} & external, "размещённые в десятках категорий не берутся"
    assert len(external) == len(sample.package.offers), "товар в двух категориях не дублируется"
    assert first.confirmed == 0 and second.confirmed == 0, (
        "категории разметки не совпадают с корнем"
    )


async def check_shortage() -> None:
    sample = await make(pages()).balanced_sample(50)
    first, second = sample.shares
    assert first.listed == 9 and first.requested == 50, "нехватка видна в итоге"
    assert second.listed == 6, "товар 1 уже взят первой категорией"
    assert len(sample.package.offers) == 15


async def check_failures() -> None:
    await expect(make({}).balanced_sample(3), SourceUnavailableError)
    await expect(make(pages() | {TREE: "<html></html>"}).balanced_sample(3), ContentFormatError)
    await expect(make(pages() | {TREE: tree()}).balanced_sample(3), ContentFormatError)
    await expect(make(pages() | {url(12): "<html></html>"}).balanced_sample(3), ContentFormatError)
    await expect(make(pages() | {url(12): script({})}).balanced_sample(3), ContentFormatError)
    missing = {key: value for key, value in pages().items() if key != url(21)}
    await expect(make(missing).balanced_sample(3), SourceUnavailableError)
    try:
        await make(pages()).balanced_sample(0)
    except ValueError:
        return
    raise AssertionError("нулевая квота должна отклоняться")


async def main() -> None:
    await check_distribution()
    await check_shortage()
    await check_failures()
    print("Проверка равномерной выборки Supl.biz пройдена")


if __name__ == "__main__":
    asyncio.run(main())
