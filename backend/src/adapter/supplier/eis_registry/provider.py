"""Поставщики и история контрактов из реестра контрактов ЕИС (zakupki.gov.ru).

Пакет содержит только компании: контракт — исторический факт, а не текущее
коммерческое предложение, поэтому `Offer` не создаются. Контракты, позиции,
цены и исполнение остаются в `contracts` и в отчёте `report` до расширения
моделей и хранилища. Период делится на окна дат, а окно, упёршееся в предел
сайта (100 страниц по 50 записей), — ещё и на диапазоны цены контракта;
неделимый срез прерывает обход. Любой пропуск страницы, сбой сети или
расхождение с общим числом результатов завершает обход ошибкой: неполный
снимок не публикуется.
"""

import asyncio
import logging
import ssl
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta

import httpx

from src.adapter.supplier import identity
from src.adapter.supplier.eis_registry import card, listing
from src.adapter.supplier.eis_registry.dto import (
    DateWindow,
    EisContract,
    EisParty,
    ListingEntry,
    Slice,
)
from src.adapter.supplier.eis_registry.http import HEADERS, EisHttp, Sleeper
from src.adapter.supplier.errors import ContentFormatError, ProviderError
from src.models.enums import VerificationStatus
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)

PROVIDER_NAME = "eis_registry"
BASE_URL = "https://zakupki.gov.ru/"


@dataclass(slots=True)
class CrawlReport:
    windows: int = 0
    pages: int = 0
    cards: int = 0
    withdrawn: int = 0
    unavailable_windows: list[str] = field(default_factory=list)


class EisRegistryProvider:
    def __init__(
        self,
        source_defaults: Source,
        period_start: date | None = None,
        period_days: int = 30,
        max_contracts: int | None = None,
        http_timeout: float = 30.0,
        max_concurrent: int = 2,
        attempts: int = 3,
        backoff: float = 2.0,
        min_interval: float = 0.0,
        sample: int | None = None,
        verify: bool | str = True,
        proxy: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleeper = asyncio.sleep,
        today: date | None = None,
    ) -> None:
        self._source = source_defaults
        self._period_start = period_start
        self._period_days = period_days
        self._max_contracts = max_contracts
        self._http_timeout = http_timeout
        self._max_concurrent = max_concurrent
        self._attempts = attempts
        self._backoff = backoff
        self._min_interval = min_interval
        self._sample = sample
        self._verify = verify
        self._proxy = proxy or None
        self._transport = transport
        self._sleep = sleep
        self._today = today
        self.contracts: tuple[EisContract, ...] = ()
        self.report = CrawlReport()

    @property
    def source(self) -> Source:
        return self._source

    def _period(self) -> DateWindow:
        end = (self._today or datetime.now(UTC).date()) - timedelta(days=1)
        start = self._period_start or end - timedelta(days=max(1, self._period_days) - 1)
        if start > end:
            raise ProviderError(f"Период обхода пуст: {start} — {end}")
        return DateWindow(start, end)

    def _verify_option(self) -> ssl.SSLContext | bool:
        if isinstance(self._verify, str):
            return ssl.create_default_context(cafile=self._verify)
        return self._verify

    async def fetch(self) -> SupplierPackage:
        report = CrawlReport()
        contracts: dict[str, EisContract] = {}
        pending = [Slice(self._period())]
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            headers=HEADERS,
            follow_redirects=True,
            proxy=self._proxy if self._transport is None else None,
            verify=self._verify_option() if self._transport is None else True,
            transport=self._transport,
        ) as client:
            http = EisHttp(
                client,
                self._max_concurrent,
                self._attempts,
                self._backoff,
                self._sleep,
                self._min_interval,
            )
            while pending:
                part = pending.pop()
                report.windows += 1
                entries = await self._slice_entries(http, part, report)
                if entries is None:
                    halves = part.narrow()
                    if halves is None:
                        raise ContentFormatError(
                            f"Срез {part} не помещается в предел выдачи сайта "
                            f"({listing.MAX_PAGES} страниц): обход был бы неполным"
                        )
                    pending.extend(reversed(halves))
                    continue
                await self._load_cards(http, entries, contracts, report)
        if not contracts:
            raise ContentFormatError("За период не прочитано ни одного контракта")
        self.report = report
        self.contracts = tuple(contracts.values())
        suppliers = self._suppliers(self.contracts)
        logger.info(
            "ЕИС: контрактов %d, поставщиков %d, срезов %d",
            len(contracts),
            len(suppliers),
            report.windows,
        )
        return SupplierPackage(self._source, tuple(suppliers.values()), ())

    async def _page(
        self, http: EisHttp, part: Slice, number: int, report: CrawlReport
    ) -> listing.ListingPage:
        url = listing.search_url(part, number)
        text = await http.get_text(url)
        report.pages += 1
        return await asyncio.to_thread(listing.parse_listing, text or "", url)

    async def _slice_entries(
        self, http: EisHttp, part: Slice, report: CrawlReport
    ) -> list[ListingEntry] | None:
        """Записи среза или None, если выдача упёрлась в предел сайта и срез надо делить.

        Сайт отдаёт не больше MAX_PAGES страниц, а следующие молча повторяют
        последнюю; общее число «более N» — только нижняя граница.
        """
        entries: dict[str, ListingEntry] = {}
        previous_first = ""
        total: int | None = None
        for number in range(1, listing.MAX_PAGES + 1):
            current = await self._page(http, part, number, report)
            if number == 1:
                total = None if current.lower_bound else current.total
            if not current.entries:
                break
            first = current.entries[0].reestr_number
            if first == previous_first:
                return None
            previous_first = first
            for entry in current.entries:
                entries.setdefault(entry.reestr_number, entry)
            if self._sample and len(entries) >= self._sample:
                return list(entries.values())[: self._sample]
            self._check_limit(len(entries))
            if len(current.entries) < listing.PAGE_SIZE:
                break
        else:
            return None
        if total is not None and len(entries) != total:
            raise ContentFormatError(
                f"За {part.window.start} — {part.window.end} прочитано {len(entries)} "
                f"из {total} контрактов: обход неполный"
            )
        return list(entries.values())

    async def _load_cards(
        self,
        http: EisHttp,
        entries: list[ListingEntry],
        contracts: dict[str, EisContract],
        report: CrawlReport,
    ) -> None:
        fresh = [e for e in entries if e.reestr_number not in contracts]
        for start in range(0, len(fresh), listing.PAGE_SIZE):
            batch = fresh[start : start + listing.PAGE_SIZE]
            loaded = await asyncio.gather(*(self._card(http, entry, report) for entry in batch))
            for contract in loaded:
                if contract is not None:
                    contracts[contract.reestr_number] = contract
            self._check_limit(len(contracts))

    def _check_limit(self, count: int) -> None:
        if self._max_contracts and count > self._max_contracts:
            raise ProviderError(
                f"Достигнут предел {self._max_contracts} контрактов: снимок был бы неполным"
            )

    async def _card(
        self, http: EisHttp, entry: ListingEntry, report: CrawlReport
    ) -> EisContract | None:
        text = await http.get_text(entry.card_url, allow_missing=True)
        if text is None:
            report.withdrawn += 1
            return None
        report.cards += 1
        contract = await asyncio.to_thread(card.parse_card, text, entry)
        items_url = listing.card_page_url(entry.card_url, "payment-info-and-target-of-order")
        items_text = await http.get_text(items_url)
        items = await asyncio.to_thread(card.parse_items, items_text or "", items_url)
        process_url = listing.card_page_url(entry.card_url, "process-info")
        process_text = await http.get_text(process_url, allow_missing=True)
        executed, paid = (None, None)
        if process_text is not None:
            executed, paid = await asyncio.to_thread(
                card.parse_execution, process_text, process_url
            )
        return replace(contract, items=items, executed_amount=executed, paid_amount=paid)

    def _suppliers(self, contracts: tuple[EisContract, ...]) -> dict[object, Supplier]:
        found: dict[object, Supplier] = {}
        for contract in contracts:
            for party in contract.suppliers:
                supplier = self._supplier(party, contract.url)
                known = found.get(supplier.supplier_id)
                if known is None:
                    found[supplier.supplier_id] = supplier
                elif party.kpp and party.kpp not in known.kpps:
                    found[supplier.supplier_id] = _with_kpp(known, party.kpp)
        return found

    def _supplier(self, party: EisParty, evidence_url: str) -> Supplier:
        key = " ".join(party.name.split()).casefold()
        return Supplier(
            supplier_id=identity.supplier_id(party.inn, self._source.source_id, key),
            name=party.name,
            inn=party.inn,
            kpps=(party.kpp,) if party.kpp else (),
            contacts={"address": party.address} if party.address else {},
            identity_status=VerificationStatus.UNVERIFIED,
            identity_evidence_url=evidence_url,
        )


def _with_kpp(supplier: Supplier, kpp: str) -> Supplier:
    return Supplier(
        supplier_id=supplier.supplier_id,
        name=supplier.name,
        inn=supplier.inn,
        kpps=(*supplier.kpps, kpp),
        legal_status=supplier.legal_status,
        region=supplier.region,
        website=supplier.website,
        contacts=supplier.contacts,
        okved_codes=supplier.okved_codes,
        identity_status=supplier.identity_status,
        identity_evidence_url=supplier.identity_evidence_url,
    )
