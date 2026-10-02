"""Диагностический живой прогон ЕИС без записи в ClickHouse.

python tests/supplier/eis_live.py --days 1 --max-contracts 40 --out report.json
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.supplier import identity
from src.adapter.supplier.eis_registry import PROVIDER_NAME, EisRegistryProvider
from src.models.catalog.source import Source
from src.models.enums import SourceType

BASE_URL = "https://zakupki.gov.ru/"


async def run(
    days: int,
    max_contracts: int,
    verify: bool | str,
    proxy: str,
    interval: float,
    out: Path | None,
    dump: Path | None,
) -> int:
    source = Source(
        source_id=identity.source_id(BASE_URL, PROVIDER_NAME),
        name="ЕИС: реестр контрактов",
        base_url=BASE_URL,
        source_type=SourceType.REGISTRY,
        provider_name=PROVIDER_NAME,
    )
    provider = EisRegistryProvider(
        source,
        period_days=days,
        verify=verify,
        proxy=proxy,
        attempts=8,
        backoff=2.0,
        min_interval=interval,
        sample=max_contracts or None,
    )
    started = time.monotonic()
    report: dict[str, object] = {"days": days, "diagnostic": True}
    status = 0
    try:
        package = await provider.fetch()
    except Exception as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        status = 1
    else:
        contracts = provider.contracts
        if dump:
            dump.write_text(
                json.dumps([asdict(c) for c in contracts], ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        pairs = [(c, s) for c in contracts for s in c.suppliers]
        report.update(
            status="ok",
            crawl=asdict(provider.report),
            contracts=len(contracts),
            items=sum(len(c.items) for c in contracts),
            suppliers=len(package.suppliers),
            supplier_inn_share=(sum(1 for _, s in pairs if s.inn) / len(pairs)) if pairs else 0,
            offers=len(package.offers),
        )
    report["seconds"] = round(time.monotonic() - started, 1)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if out:
        out.write_text(text, encoding="utf-8")
    print(text)
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--max-contracts", type=int, default=40)
    parser.add_argument("--ca-bundle", default="")
    parser.add_argument("--proxy", default="")
    parser.add_argument("--interval", type=float, default=1.5)
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--dump", type=Path)
    args = parser.parse_args()
    verify = args.ca_bundle or (not args.insecure)
    sys.exit(
        asyncio.run(
            run(
                args.days,
                args.max_contracts,
                verify,
                args.proxy,
                args.interval,
                args.out,
                args.dump,
            )
        )
    )
