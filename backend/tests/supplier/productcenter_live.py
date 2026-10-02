"""Живой полный обход ProductCenter с отчётом вне Git.

Запускать после локальных тестов. Скрипт не записывает пакет в ClickHouse.
"""

import argparse
import asyncio
import json
import logging
import resource
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.supplier import identity
from src.adapter.supplier.productcenter_web import ProductCenterWebProvider
from src.models.catalog.source import Source
from src.models.enums import SourceType


async def git_state() -> tuple[str, bool]:
    async def output(*args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "git", *args, cwd=ROOT.parent, stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return stdout.decode().strip() if process.returncode == 0 else ""

    return await output("rev-parse", "HEAD"), bool(await output("status", "--porcelain"))


async def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument(
        "--out", type=Path, default=Path(tempfile.gettempdir()) / "productcenter-report.json"
    )
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--request-interval", type=float, default=1.0)
    parser.add_argument("--connection-retries", type=int, default=180)
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    base_url = "https://productcenter.ru/"
    source = Source(
        source_id=identity.source_id(base_url, "productcenter_web"),
        name="ПродуктЦентр",
        base_url=base_url,
        source_type=SourceType.DIRECTORY,
        provider_name="productcenter_web",
    )
    provider = ProductCenterWebProvider(
        source,
        max_concurrent=args.parallel,
        http_timeout=args.timeout,
        request_interval=args.request_interval,
        connection_retries=args.connection_retries,
        cache_dir=args.cache_dir,
    )
    started = time.monotonic()
    revision, dirty = await git_state()
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "parallel": args.parallel,
        "request_interval": args.request_interval,
        "connection_retries": args.connection_retries,
        "revision": revision,
        "dirty_worktree": dirty,
    }
    try:
        package = await provider.fetch()
        report.update(
            status="success",
            companies=len(package.suppliers),
            offers=len(package.offers),
            inn_count=sum(bool(s.inn) for s in package.suppliers),
            linked_offers=sum(bool(o.supplier_id) for o in package.offers),
            categories=len({o.source_category for o in package.offers if o.source_category}),
            regions=len({s.region for s in package.suppliers if s.region}),
        )
    except Exception as error:
        causes = error.exceptions if isinstance(error, ExceptionGroup) else (error,)
        report.update(
            status="failed",
            errors=[f"{type(cause).__name__}: {cause}" for cause in causes],
        )
    report.update(
        finished_at=datetime.now(UTC).isoformat(),
        elapsed_seconds=round(time.monotonic() - started, 2),
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        * (1024 if sys.platform.startswith("linux") else 1),
        stats=provider.stats,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(
        args.out.write_text, json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(run())
