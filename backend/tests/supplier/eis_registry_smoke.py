"""Проверки адаптера реестра контрактов ЕИС на искусственных страницах без сети."""

import asyncio
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.supplier import identity
from src.adapter.supplier.eis_registry import EisRegistryProvider
from src.adapter.supplier.eis_registry.dto import DateWindow
from src.adapter.supplier.errors import ContentFormatError, ProviderError, SourceUnavailableError
from src.models.catalog.source import Source
from src.models.enums import SourceType

SOURCE = Source(
    source_id=identity.source_id("https://zakupki.gov.ru/", "eis_registry"),
    name="ЕИС: реестр контрактов",
    base_url="https://zakupki.gov.ru/",
    source_type=SourceType.REGISTRY,
    provider_name="eis_registry",
)
CARD = "https://zakupki.gov.ru/epz/contract/contractCard/common-info.html?reestrNumber={}"
INN_A = "7707083893"


def number(index):
    return f"2770708389326{index:06d}"


def block(index):
    return f"""<div class="search-registry-entry-block box-shadow-search-input">
<div class="registry-entry__header-mid align-items-center mt-4">
<div class="registry-entry__header-mid__number">
<a target="_blank" href="/epz/contract/contractCard/common-info.html?reestrNumber={number(index)}">
№ {number(index)}</a></div>
<div class="registry-entry__header-mid__title">Исполнение</div></div>
<div class="registry-entry__body-block"><div class="registry-entry__body-title">Заказчик</div>
<div class="registry-entry__body-href"><a href="/epz/organization/view/info.html?organizationId=7">
ГБУ Школа {index}</a></div></div></div>"""


def listing(total, indexes, prefix=""):
    body = "".join(block(i) for i in indexes)
    return (
        '<html><body><div class="search-results__total">'
        f"{prefix} {total} записей</div>{body}</body></html>"
    )


def card(inn=INN_A, kpp="770701001", with_supplier=True):
    supplier = (
        f"""<table class="blockInfo__table tableBlock"><thead><tr class="tableBlock__row">
<th class="tableBlock__col_header">Организация</th><th>Страна, код</th>
<th>Адрес места нахождения</th><th>Телефон, электронная почта</th><th></th></tr></thead>
<tbody class="tableBlock__body"><tr class="tableBlock__row"><td class="tableBlock__col_first">
ООО "РОМАШКА"
<section class="blockInfo__section section"><span class="grey-main-light">Код по ОКПО:</span> <span>17514186</span></section>
<section class="section"><span class="grey-main-light">ИНН:</span> <span>{inn}</span></section>
<section><span class="grey-main-light">КПП:</span> <span>{kpp}</span></section></td>
<td>Российская Федерация <br>643</td><td>191002 г. Санкт-Петербург, ул. Достоевского,15</td>
<td>8-3022-353279 <br>708@rt.ru</td><td></td></tr></tbody></table>"""
        if with_supplier
        else ""
    )
    return f"""<html><body>
<span class="cardMainInfo__state distancedText"> Исполнение </span>
<span class="cardMainInfo__title">Цена контракта</span><span class="cardMainInfo__content cost">
1 250,50&nbsp;&#8381;</span>
<section class="section"><span class="section__title">Дата заключения контракта</span>
<span class="section__info">02.09.2026</span></section>
<section class="section"><span class="section__title">Дата окончания исполнения контракта</span>
<span class="section__info">31.12.2026</span></section>
{supplier}</body></html>"""


def items_page(with_table=True):
    if not with_table:
        return "<html><body><h2>Объекты закупки</h2></body></html>"
    return """<html><body><table class="tableBlock"><thead><tr><th>Код бюджетной классификации</th>
<th></th><th>Сумма контракта на декабрь 2026 год, ₽</th></tr></thead>
<tr><td>037 0113</td><td></td><td>312 532,90</td></tr></table>
<table class="blockInfo__table tableBlock" id="contract_subjects"><thead><tr class="tableBlock__row">
<th></th><th>Наименование объекта закупки и его характеристики</th>
<th>Позиции по КТРУ, ОКПД2</th><th>Тип объекта закупки</th>
<th>Количество товара, объем работы, услуги,<br>Единица измерения</th>
<th>Цена за единицу измерения, ₽</th><th>Сумма, ₽</th></tr></thead>
<tbody class="tableBlock__body"><tr class="tableBlock__row "><td></td>
<td><div>Бумага А4</div></td><td>17.12.14.110-00000002</td><td>Не указан</td>
<td><div class="w-space-nowrap">10 пачка<div class="help-icon" data-tooltip='<span>Пачка</span>'></div></div></td>
<td>125,05</td><td>1 250,50 <span class="section__title">Ставка НДС: Без НДС</span></td></tr>
<tr class="tableBlock__row 23027069 hidden"><td></td><td colspan="6"><div></div></td></tr>
</tbody></table></body></html>"""


def process_page():
    return """<html><body><table class="blockInfo__table tableBlock"><thead><tr>
<th colspan="2" class="tableBlock__col_right">Этап контракта</th>
<th>Стоимость исполненных<br> обязательств,&nbsp;₽</th><th>Фактически оплачено,&nbsp; ₽ </th>
<th>Документы</th><th>Неустойки</th><th>Исполнение <br> завершено</th></tr></thead>
<tr><td><span></span></td><td>По 02.04.2026</td><td>1 000,00</td><td>400,00</td><td></td><td></td><td></td></tr>
<tr><td><span></span></td><td>По 31.12.2026</td><td>250,50</td><td>250,50</td><td></td><td></td><td></td></tr>
</table></body></html>"""


def page_response(path, common):
    if path.endswith("payment-info-and-target-of-order.html"):
        return httpx.Response(200, text=items_page())
    if path.endswith("process-info.html"):
        return httpx.Response(200, text=process_page())
    return httpx.Response(200, text=common)


def make(total=3, per_page=50, **options):
    calls = []

    def respond(request):
        calls.append(str(request.url))
        parts = urlsplit(str(request.url))
        if parts.path.endswith("/results.html"):
            query = parse_qs(parts.query)
            page_number = int(query["pageNumber"][0])
            start = (page_number - 1) * per_page
            indexes = range(start, min(start + per_page, total))
            return httpx.Response(200, text=listing(total, indexes))
        return page_response(parts.path, card())

    handler = options.pop("handler", respond)
    options.setdefault("period_days", 1)
    adapter = EisRegistryProvider(
        SOURCE,
        transport=httpx.MockTransport(handler),
        today=date(2026, 10, 1),
        backoff=0,
        sleep=lambda _: asyncio.sleep(0),
        **options,
    )
    return adapter, calls


async def expect_error(adapter, error_type):
    try:
        await adapter.fetch()
    except error_type:
        return
    raise AssertionError(f"Ожидалась ошибка {error_type.__name__}")


def test_window():
    window = DateWindow(date(2026, 1, 1), date(2026, 1, 5))
    left, right = window.split()
    assert (left.start, left.end) == (date(2026, 1, 1), date(2026, 1, 3))
    assert (right.start, right.end) == (date(2026, 1, 4), date(2026, 1, 5))
    two = DateWindow(date(2026, 1, 1), date(2026, 1, 2)).split()
    assert two[0].days() == two[1].days() == 1


async def run():
    test_window()
    paged, paged_calls = make(total=120)
    many = await paged.fetch()
    assert len(paged.contracts) == 120 and len(many.suppliers) == 1, "Дедупликация поставщика"
    assert sum("results.html" in c for c in paged_calls) == 3, "Три страницы по 50"
    adapter, _ = make()
    first = await adapter.fetch()
    second = await adapter.fetch()
    assert len(adapter.contracts) == 3
    assert not first.offers, "Исторические контракты не должны становиться Offer"
    assert first.source.source_type == SourceType.REGISTRY
    assert {s.inn for s in first.suppliers} <= {INN_A}
    assert {s.supplier_id for s in first.suppliers} == {s.supplier_id for s in second.suppliers}
    assert all(s.kpps == ("770701001",) for s in first.suppliers)
    contract = adapter.contracts[0]
    assert contract.price is not None and str(contract.price) == "1250.50"
    assert contract.status == "Исполнение" and contract.signed_on == "02.09.2026"
    assert contract.execution_end == "31.12.2026" and contract.customer == "ГБУ Школа 0"
    assert str(contract.executed_amount) == "1250.50" and str(contract.paid_amount) == "650.50"
    assert first.suppliers[0].name == 'ООО "РОМАШКА"', "Название без ИНН и КПП"
    assert "Санкт-Петербург" in first.suppliers[0].contacts["address"]
    item = contract.items[0]
    assert (item.okpd2_code, item.unit, str(item.quantity)) == ("17.12.14.110", "пачка", "10")
    assert str(item.unit_price) == "125.05" and str(item.total_price) == "1250.50"
    assert adapter.report.pages == 1 and adapter.report.cards == 3

    # Та же компания с другим КПП: копия обязана сохранить остальные поля.
    second_kpp, _ = make(
        total=2,
        per_page=2,
        handler=lambda r: (
            httpx.Response(200, text=listing(2, [0, 1]))
            if "results" in r.url.path
            else page_response(
                r.url.path,
                card(kpp="780101001" if "000001" in str(r.url) else "770701001"),
            )
        ),
    )
    merged = await second_kpp.fetch()
    assert len(merged.suppliers) == 1, "Компания с двумя КПП остаётся одной записью"
    assert set(merged.suppliers[0].kpps) == {"770701001", "780101001"}
    assert merged.suppliers[0].inn == INN_A and merged.suppliers[0].name == 'ООО "РОМАШКА"'
    assert merged.suppliers[0].contacts.get("address"), "Контакты не теряются при добавлении КПП"

    bad_inn, _ = make(
        total=1,
        per_page=1,
        handler=lambda r: (
            httpx.Response(200, text=listing(1, [0]))
            if "results" in r.url.path
            else page_response(r.url.path, card(inn="1234567890"))
        ),
    )
    package = await bad_inn.fetch()
    assert package.suppliers[0].inn is None, "Неверный ИНН не принимается"

    async def check(handler, error_type, **options):
        broken, _ = make(handler=handler, **options)
        await expect_error(broken, error_type)

    def html(text):
        return lambda r: httpx.Response(200, text=text)

    await check(html("<html><body>Проверка доступа</body></html>"), ContentFormatError)
    await check(html("<html><body>Ничего не найдено</body></html>"), ContentFormatError)
    await check(
        lambda r: httpx.Response(200, text=listing(0, [])) if "results" in r.url.path else None,
        ContentFormatError,
    )
    await check(
        lambda r: (
            httpx.Response(200, text=listing(1, [0]))
            if "results" in r.url.path
            else page_response(r.url.path, card(with_supplier=False))
        ),
        ContentFormatError,
        total=1,
    )
    await check(
        lambda r: (
            httpx.Response(200, text=listing(1, [0]))
            if "results" in r.url.path
            else httpx.Response(200, text=items_page(False) if "payment" in r.url.path else card())
        ),
        ContentFormatError,
    )
    await check(
        lambda r: httpx.Response(200, text=listing(5, [0, 1])),
        ContentFormatError,
    )

    def refuse(request):
        raise httpx.ConnectError("network", request=request)

    await check(refuse, SourceUnavailableError)
    await check(lambda r: httpx.Response(403), SourceUnavailableError)
    await check(lambda r: httpx.Response(500), SourceUnavailableError)
    await check(lambda r: httpx.Response(200, text=listing(5000, [0])), ContentFormatError)

    def lower_bound(request):
        if "results" in request.url.path:
            return httpx.Response(200, text=listing(1, [0], "более"))
        return page_response(request.url.path, card())

    lower = make(handler=lower_bound)[0]
    assert len((await lower.fetch()).suppliers) == 1, "«более N» — не точное число"

    def overflow(request):
        query = parse_qs(urlsplit(str(request.url)).query)
        if "results" not in request.url.path:
            return page_response(request.url.path, card())
        if "contractPriceFrom" in query:
            return httpx.Response(200, text=listing(1, [0]))
        return httpx.Response(200, text=listing(9000, range(50), "более"))

    split, _ = make(handler=overflow, period_days=4)
    await split.fetch()
    assert split.report.windows == 15, "Дни делятся пополам, затем каждый день — по цене"
    assert len(split.contracts) == 1, "Дедупликация между срезами"

    def endless(request):
        if "results" not in request.url.path:
            return page_response(request.url.path, card())
        return httpx.Response(200, text=listing(9000, range(50), "более"))

    await check(endless, ContentFormatError)
    limited, _ = make(max_contracts=1)
    await expect_error(limited, ProviderError)

    attempts = {"count": 0}

    def flaky(request):
        if "results" in request.url.path:
            attempts["count"] += 1
            if attempts["count"] == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, text=listing(1, [0]))
        return page_response(request.url.path, card())

    retried, _ = make(handler=flaky)
    assert len((await retried.fetch()).suppliers) == 1 and attempts["count"] == 2

    def withdrawn(request):
        if "results" in request.url.path:
            return httpx.Response(200, text=listing(2, [0, 1]))
        return (
            httpx.Response(404)
            if number(0) in str(request.url)
            else page_response(request.url.path, card())
        )

    gone, _ = make(handler=withdrawn)
    await gone.fetch()
    assert gone.report.withdrawn == 1 and len(gone.contracts) == 1
    assert re.fullmatch(r"\d{10,}", gone.contracts[0].reestr_number)
    print("eis_registry_smoke: ok")


if __name__ == "__main__":
    asyncio.run(run())
