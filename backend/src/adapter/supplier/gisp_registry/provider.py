"""Снимок официальных перечней организаций и продукции ПП 719 ГИСП."""

import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.gisp_registry.api import parse_organizations, parse_products
from src.adapter.supplier.gisp_registry.snapshot import parse_snapshot
from src.adapter.supplier.gisp_registry.supplier import merge_supplier
from src.adapter.supplier.gisp_registry.workbook import parse_workbook
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
)
PRODUCT_PAGE_SIZE = 100
ORGANIZATION_PAGE_SIZE = 1000
MAX_ATTEMPTS = 4
logger = logging.getLogger(__name__)


def _row_fingerprint(item: dict[str, object]) -> bytes:
    encoded = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).digest()


class GispRegistryProvider:
    def __init__(
        self,
        source_defaults: Source,
        export_location: str,
        http_timeout: float = 120.0,
        max_concurrent: int = 4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._export_location = export_location
        self._http_timeout = http_timeout
        self._max_concurrent = max(1, max_concurrent)
        self._transport = transport

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        if not self._export_location:
            return await self._fetch_api()
        parsed = urlsplit(self._export_location)
        if parsed.scheme in ("https", "http"):
            content = await self._download()
        elif parsed.scheme == "file":
            path = Path(parsed.path)
            if await asyncio.to_thread(path.is_dir):
                return await asyncio.to_thread(parse_snapshot, path, self._source)
            try:
                content = await asyncio.to_thread(path.read_bytes)
            except OSError as error:
                raise SourceUnavailableError(str(error)) from error
        else:
            raise SourceUnavailableError("GISP_EXPORT_LOCATION: нужен HTTPS или file://")
        try:
            product_package = await asyncio.to_thread(parse_workbook, content, self._source)
        except ContentFormatError:
            raise
        except Exception as error:
            raise ContentFormatError(f"Выгрузка ГИСП не разобрана: {error}") from error
        async with self._client() as http:
            suppliers = await self._organizations(http)
        for supplier in product_package.suppliers:
            previous = suppliers.get(supplier.supplier_id)
            suppliers[supplier.supplier_id] = (
                merge_supplier(previous, supplier) if previous else supplier
            )
        return SupplierPackage(
            source=self._source,
            suppliers=tuple(suppliers.values()),
            offers=product_package.offers,
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            transport=self._transport,
        )

    async def _organizations(self, http: httpx.AsyncClient) -> dict[UUID, Supplier]:
        suppliers: dict[UUID, Supplier] = {}
        async for page in self._pages(http, "org", ORGANIZATION_PAGE_SIZE):
            for supplier in await asyncio.to_thread(parse_organizations, page, self._source):
                previous = suppliers.get(supplier.supplier_id)
                suppliers[supplier.supplier_id] = (
                    merge_supplier(previous, supplier) if previous else supplier
                )
        return suppliers

    async def _fetch_api(self) -> SupplierPackage:
        observed_at = datetime.now(UTC)
        offers = {}
        async with self._client() as http:
            suppliers = await self._organizations(http)
            logger.info("ГИСП: организаций из перечня — %d", len(suppliers))
            async for page in self._pages(http, "prod", PRODUCT_PAGE_SIZE):
                parsed = await asyncio.to_thread(parse_products, page, self._source, observed_at)
                for supplier, offer in parsed:
                    previous_supplier = suppliers.get(supplier.supplier_id)
                    suppliers[supplier.supplier_id] = (
                        merge_supplier(previous_supplier, supplier)
                        if previous_supplier
                        else supplier
                    )
                    previous = offers.get(offer.external_id)
                    if previous and previous.content_hash != offer.content_hash:
                        raise ContentFormatError(f"ГИСП: противоречивый дубль {offer.external_id}")
                    offers[offer.external_id] = offer
        if not offers:
            raise ContentFormatError("ГИСП: реестр продукции пуст")
        logger.info("ГИСП: компаний — %d, версий продукции — %d", len(suppliers), len(offers))
        return SupplierPackage(
            source=self._source,
            suppliers=tuple(suppliers.values()),
            offers=tuple(offers.values()),
        )

    async def _pages(
        self, http: httpx.AsyncClient, kind: str, page_size: int
    ) -> AsyncIterator[list[dict[str, object]]]:
        first, total = await self._page(http, kind, 0, page_size, count=True)
        if total is None or total < len(first) or not first:
            raise ContentFormatError(f"ГИСП {kind}: неверное число записей")
        if len(first) != min(page_size, total):
            raise ContentFormatError(f"ГИСП {kind}: первая страница неполная")
        seen_rows = {_row_fingerprint(item) for item in first}
        read_count = len(first)
        yield first
        offsets = range(page_size, total, page_size)
        for start in range(0, len(offsets), self._max_concurrent):
            group = [
                offsets[index]
                for index in range(start, min(start + self._max_concurrent, len(offsets)))
            ]
            pages = await asyncio.gather(
                *(self._page(http, kind, offset, page_size) for offset in group)
            )
            for offset, (page, _) in zip(group, pages, strict=True):
                if len(page) != min(page_size, total - offset):
                    raise ContentFormatError(
                        f"ГИСП {kind}: страница {offset} неполная ({len(page)})"
                    )
                fingerprints = {_row_fingerprint(item) for item in page}
                if fingerprints & seen_rows:
                    raise ContentFormatError(
                        f"ГИСП {kind}: повтор записи на странице {offset}; "
                        "полнота пагинации не подтверждена"
                    )
                seen_rows.update(fingerprints)
                read_count += len(page)
                yield page
            if start and start % 100 == 0:
                logger.info("ГИСП %s: прочитано %d/%d", kind, read_count, total)
        end_first, end_total = await self._page(http, kind, 0, page_size, count=True)
        if read_count != total or end_total != total or end_first != first:
            raise ContentFormatError(f"ГИСП {kind}: число записей изменилось во время обхода")

    async def _page(
        self,
        http: httpx.AsyncClient,
        kind: str,
        offset: int,
        size: int,
        count: bool = False,
    ) -> tuple[list[dict[str, object]], int | None]:
        url = f"https://gisp.gov.ru/pp719v2/pub/{kind}/b/"
        payload = {"opt": {"skip": offset, "take": size, "requireTotalCount": count}}
        for attempt in range(MAX_ATTEMPTS):
            response: httpx.Response | None = None
            try:
                response = await http.post(url, json=payload)
                response.raise_for_status()
                if "text/html" in response.headers.get("content-type", "").lower():
                    raise SourceUnavailableError(
                        f"ГИСП {kind}, страница {offset}: "
                        "вместо JSON получена HTML-проверка доступа"
                    )
                data = await asyncio.to_thread(response.json)
                if not isinstance(data, dict) or data.get("ok") is not True:
                    raise ContentFormatError(f"ГИСП {kind}: некорректный ответ {offset}")
                items = data.get("items")
                total = data.get("total_count")
                if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                    raise ContentFormatError(f"ГИСП {kind}: неверные строки {offset}")
                if count and (not isinstance(total, int) or total < 0):
                    raise ContentFormatError(f"ГИСП {kind}: нет общего числа строк")
                return items, total if isinstance(total, int) else None
            except (httpx.HTTPError, ValueError) as error:
                if attempt == MAX_ATTEMPTS - 1:
                    raise SourceUnavailableError(
                        f"ГИСП {kind}, страница {offset}: {error}"
                    ) from error
                retry_after = response.headers.get("Retry-After", "") if response else ""
                delay = float(retry_after) if retry_after.isdigit() else 2**attempt
                await asyncio.sleep(min(delay, 30.0))
        raise SourceUnavailableError(f"ГИСП {kind}, страница {offset}: попытки исчерпаны")

    async def _download(self) -> bytes:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._http_timeout),
                follow_redirects=True,
                transport=self._transport,
            ) as http:
                response = await http.get(
                    self._export_location,
                    headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
                )
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as error:
            raise SourceUnavailableError(f"Выгрузка ГИСП недоступна: {error}") from error
