"""Адаптер исходного датасета задачи: компании из CSV поставщиков.

`Поставщики_24-25.csv` содержит `lot_id`, `supplier_inn`, `supplier_kpp` и
`is_winner`. Названий и ассортимента в файле нет, поэтому адаптер отдаёт
компании по ИНН без предложений: наименование и реквизиты добавит обогащение по
реестру. Участие в лотах здесь не импортируется — это отдельная задача.

Файл читается без сети: чтение блокирующее, поэтому идёт в пуле потоков.
"""

import asyncio
import csv
import logging
from pathlib import Path

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.inn import normalize_inn, normalize_kpp
from src.models.enums import VerificationStatus
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)

PROVIDER_NAME = "supplier_dataset"


class SupplierDatasetProvider:
    """Читает CSV поставщиков из локального файла."""

    def __init__(
        self,
        source_defaults: Source,
        dataset_path: Path,
        region: str = "",
        delimiter: str = ",",
        encoding: str = "utf-8-sig",
    ) -> None:
        self._source = source_defaults
        self._path = dataset_path
        self._region = region
        self._delimiter = delimiter
        self._encoding = encoding

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        if not await asyncio.to_thread(self._path.is_file):
            raise SourceUnavailableError(f"файл датасета не найден: {self._path}")
        rows = await asyncio.to_thread(self._read_rows)
        suppliers = self._suppliers(rows)
        logger.info("Датасет %s: компаний — %d", self._path.name, len(suppliers))
        return SupplierPackage(source=self._source, suppliers=tuple(suppliers))

    def _read_rows(self) -> list[dict[str, str]]:
        with self._path.open("r", encoding=self._encoding, newline="") as handle:
            reader = csv.DictReader(handle, delimiter=self._delimiter)
            fieldnames = list(reader.fieldnames or ())
            if "supplier_inn" not in fieldnames:
                raise ContentFormatError(
                    f"{self._path}: в файле нет колонки supplier_inn: {fieldnames}"
                )
            return list(reader)

    def _suppliers(self, rows: list[dict[str, str]]) -> list[Supplier]:
        """Компания встречается в датасете много раз: в пакете остаётся одна запись."""
        unique: dict[str, Supplier] = {}
        evidence_url = self._path.resolve().as_uri()
        for row in rows:
            inn = normalize_inn(row.get("supplier_inn"))
            if inn is None:
                # Строка без пригодного ИНН не создаёт компанию: ключ был бы ненадёжным.
                logger.debug("Пропущена строка без корректного ИНН: %r", row.get("supplier_inn"))
                continue
            kpp = normalize_kpp(row.get("supplier_kpp"))
            supplier = Supplier(
                supplier_id=identity.supplier_id(inn, self._source.source_id, inn),
                # Название в датасете отсутствует: его добавляет обогащение по реестру.
                name=(row.get("supplier_name") or "").strip(),
                inn=inn,
                kpps=(kpp,) if kpp else (),
                region=self._region,
                # Участие в закупке не подтверждает реквизиты: проверка идёт по реестру.
                identity_status=VerificationStatus.UNVERIFIED,
                identity_evidence_url=evidence_url,
            )
            current = unique.get(inn)
            if current is None or (not current.kpps and supplier.kpps):
                unique[inn] = supplier
        return list(unique.values())
