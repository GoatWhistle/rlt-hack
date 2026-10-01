"""Команда запуска джобы синхронизации источников и обслуживания схемы.

Контроллер разбирает аргументы и вызывает слои через интерфейсы из protocols;
бизнес-логики здесь нет. Источники обходятся конкурентно внутри сервиса.
"""

import argparse
import asyncio
import dataclasses
import logging
import sys
from collections.abc import Sequence
from uuid import UUID

from src.application.config import AppConfig
from src.application.container import Container
from src.controller.job.dto import NormalizeCommand, SyncCommand
from src.controller.job.protocols import (
    CoverageReading,
    CrawlJournalReader,
    OfferEnriching,
    OfferReidentifying,
    SchemaMigrator,
    SourceCatalog,
    SupplierSyncing,
)
from src.models.coverage import CoverageReport
from src.service.errors import ProviderNotConfiguredError, ServiceError

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sync-job",
        description="Джоба сбора поставщиков и их товаров",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("migrate", help="применить миграции ClickHouse")
    commands.add_parser("migrations", help="показать применённые миграции")
    commands.add_parser("providers", help="показать подключённые адаптеры источников")
    commands.add_parser("sources", help="показать источники, уже записанные в хранилище")

    runs = commands.add_parser("runs", help="последние обходы источника")
    runs.add_argument("--source", required=True, help="UUID источника")
    runs.add_argument("--limit", type=int, default=10)

    normalize = commands.add_parser(
        "normalize", help="пересчитать нормализацию и классификацию сохранённых позиций"
    )
    normalize.add_argument(
        "--limit",
        type=int,
        default=None,
        help="сколько позиций пересчитать: по умолчанию все",
    )

    commands.add_parser("coverage", help="отчёт о покрытии нормализации и классификации")

    commands.add_parser(
        "reidentify",
        help="перевести сохранённые позиции на действующее правило ключа источника",
    )

    sync = commands.add_parser("sync", help="обойти все подключённые источники")
    sync.add_argument(
        "--forever",
        action="store_true",
        help="повторять обход с интервалом SYNC_INTERVAL_SECONDS",
    )
    sync.add_argument(
        "--parallel",
        type=int,
        default=None,
        help="сколько источников обходить одновременно",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    config = AppConfig.from_env()
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return asyncio.run(_dispatch(arguments, config))
    except ServiceError as error:
        print(f"Ошибка: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        logger.exception("Команда %s не выполнена", arguments.command)
        print(f"Сбой: {type(error).__name__}: {error}", file=sys.stderr)
        return 3


async def _dispatch(arguments: argparse.Namespace, config: AppConfig) -> int:
    if arguments.command == "sync":
        return await _sync(arguments, config)
    async with Container(config) as container:
        if arguments.command == "providers":
            for provider in container.providers():
                source = provider.source
                print(f"{source.source_id}  {source.provider_name:18}  {source.name}")
            return 0
        migrator: SchemaMigrator = await container.migrator()
        if arguments.command == "migrate":
            applied = await migrator.apply_pending()
            print("\n".join(applied) if applied else "Новых миграций нет")
            return 0
        if arguments.command == "migrations":
            names = await migrator.applied_names()
            print("\n".join(names) or "Миграции не применялись")
            return 0
        if arguments.command == "sources":
            catalog: SourceCatalog = await container.sources()
            for source in await catalog.list_all():
                print(f"{source.source_id}  {source.provider_name:18}  {source.name}")
            return 0
        if arguments.command == "normalize":
            command = NormalizeCommand.of(arguments)
            enriching: OfferEnriching = await container.enrichment()
            result = await enriching.run(command.limit)
            print(
                f"Источников: {result.sources}  позиций: {result.offers}  "
                f"с кодом: {result.classified}  "
                f"правила: {result.normalizer_version} / {result.classifier_version}"
            )
            return 0
        if arguments.command == "reidentify":
            reidentifying: OfferReidentifying = await container.reidentify()
            outcome = await reidentifying.run()
            print(
                f"Источников: {outcome.sources}  позиций: {outcome.offers}  "
                f"сменили ключ: {outcome.changed}  слились: {outcome.merged}"
            )
            return 0
        if arguments.command == "coverage":
            reading: CoverageReading = await container.enrichment()
            _print_coverage(await reading.coverage())
            return 0
        if arguments.command == "runs":
            journal: CrawlJournalReader = await container.journal()
            for run in await journal.last_runs(UUID(arguments.source), arguments.limit):
                print(
                    f"{run.started_at:%Y-%m-%d %H:%M:%S}  {run.status:8}  "
                    f"{run.provider_name:18}  компаний={run.suppliers_extracted}  "
                    f"предложений={run.offers_extracted}  {run.error_message}"
                )
            return 0
    raise ServiceError(f"неизвестная команда: {arguments.command}")


def _print_coverage(report: CoverageReport) -> None:
    """Покрытие показывается долями: пустые поля видно так же, как заполненные."""
    total = report.offers or 1
    print(f"Позиций: {report.offers}")
    for title, value in (
        ("нормализовано", report.normalized),
        ("с кодом ОКПД2", report.classified),
        ("с рубрикой", report.with_rubric),
        ("с единицей ОКЕИ", report.with_unit),
        ("с ценой за единицу", report.with_price_per_unit),
        ("с брендом", report.with_brand),
        ("с артикулом", report.with_article),
        ("с характеристиками", report.with_attributes),
    ):
        print(f"  {title:22} {value:7}  {value / total:6.1%}")
    for title, shares in (
        ("Каналы классификации", report.by_method),
        ("Тип позиции", report.by_item_type),
        ("Уровень кода", report.by_level),
        ("Рубрики", report.by_rubric),
    ):
        print(f"{title}:")
        for share in shares:
            name = share.name or "—"
            print(f"  {name:22} {share.offers:7}  {share.offers / total:6.1%}")


async def _sync(arguments: argparse.Namespace, config: AppConfig) -> int:
    command = SyncCommand.of(arguments)
    if command.parallel_sources is not None:
        config = dataclasses.replace(config, parallel_sources=command.parallel_sources)
    async with Container(config) as container:
        worker: SupplierSyncing = await container.supplier_worker()
        if not container.providers():
            raise ProviderNotConfiguredError(
                "ни один адаптер источника не включён: задайте флаги *_PROVIDER"
            )
        if command.forever:
            await worker.run_forever()
            return 0
        result = await worker.run_once()
    for item in result.sources:
        print(
            f"{item.provider_name:18}  {item.status:8}  компаний={item.suppliers_extracted}  "
            f"предложений={item.offers_extracted}  снято={item.offers_withdrawn}  "
            f"{item.error_message}"
        )
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
