"""Выборка товаров Supl.biz поровну по корневым категориям.

Запуск из каталога `backend`:

    PYTHONPATH=. uv run --no-project --python 3.13 --with httpx \
        python scripts/supl_biz_balanced_sample.py --per-category 300 --out /path/outside/git.json

Результат пишется только в указанный файл, в ClickHouse ничего не сохраняется.
Выборка диагностическая: она не заменяет полный снимок источника.
"""

import argparse
import asyncio
import json
import logging
import time
from dataclasses import asdict
from pathlib import Path

from src.adapter.supplier import identity
from src.adapter.supplier.supl_biz_web import PROVIDER_NAME, SuplBizWebProvider
from src.models.catalog.source import Source
from src.models.enums import SourceType

BASE_URL = "https://supl.biz/"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--per-category", type=int, default=300)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


async def run(arguments: argparse.Namespace) -> None:
    source = Source(
        source_id=identity.source_id(BASE_URL, PROVIDER_NAME),
        name="Supl.biz",
        base_url=BASE_URL,
        source_type=SourceType.DIRECTORY,
        provider_name=PROVIDER_NAME,
    )
    provider = SuplBizWebProvider(source, max_concurrent=arguments.concurrency, retries=4)
    started = time.monotonic()
    sample = await provider.balanced_sample(arguments.per_category)
    package = sample.package
    print(f"время {time.monotonic() - started:.0f} с")
    print(f"предложений {len(package.offers)}, компаний {len(package.suppliers)}")
    print(f"ИНН у {sum(bool(s.inn) for s in package.suppliers)} компаний")
    print(f"цена у {sum(o.price is not None for o in package.offers)} предложений")
    for share in sample.shares:
        line = (
            f"запрошено {share.requested}, найдено {share.listed}, "
            f"прочитано {share.fetched}, подтверждено разметкой {share.confirmed}"
        )
        print(f"{share.name}: {line}")
    document = {
        "shares": [asdict(share) for share in sample.shares],
        "suppliers": [asdict(s) for s in package.suppliers],
        "offers": [asdict(o) for o in package.offers],
    }
    arguments.out.write_text(json.dumps(document, ensure_ascii=False, default=str))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(parse_arguments()))


if __name__ == "__main__":
    main()
