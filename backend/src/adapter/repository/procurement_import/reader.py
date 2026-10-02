import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import duckdb

from src.adapter.supplier.identity import NAMESPACE, supplier_id


class ArchiveReader:
    def __init__(self, path: Path, before: date, index_id: str, spill: Path) -> None:
        self.before = before
        self.index_id = index_id
        self.connection = duckdb.connect(str(path), read_only=True)
        try:
            self.connection.execute("SET memory_limit='512MB'")
            self.connection.execute("SET threads=1")
            self.connection.execute("SET preserve_insertion_order=false")
            self.connection.execute("SET temp_directory=?", [str(spill)])
            self.connection.execute(
                "CREATE TEMP TABLE eligible_lots AS SELECT * FROM lot_info "
                "WHERE publish_date < ? AND NOT notice_conflict",
                [before],
            )
        except BaseException:
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def counts(self) -> tuple[int, ...]:
        return tuple(
            int(self.connection.execute(query).fetchall()[0][0])
            for query in (
                "SELECT count(*) FROM eligible_lots",
                "SELECT count(*) FROM products SEMI JOIN eligible_lots USING(lot_id)",
                "SELECT count(*) FROM participations SEMI JOIN eligible_lots USING(lot_id)",
            )
        )

    def start(self, table: str) -> None:
        queries = {
            "procurement_lots": "SELECT lot_id, coalesce(procedure_id,''), "
            "procedure_name, subject, "
            "try_cast(start_price AS DECIMAL(18,2)), is_smp, customer_inn, source_system, "
            "publish_date FROM eligible_lots",
            "procurement_items": "SELECT p.lot_id, p.product_name, coalesce(p.okpd2_code,'') "
            "FROM products p SEMI JOIN eligible_lots USING(lot_id)",
            "lot_participations": "SELECT p.lot_id, p.supplier_inn, "
            "(p.is_winner AND NOT p.label_conflict AND l.winner_count=1), "
            "CASE WHEN p.label_conflict OR l.winner_count>1 "
            "THEN 'unconfirmed' ELSE 'confirmed' END "
            "FROM participations p JOIN eligible_lots l USING(lot_id)",
        }
        self.connection.execute(queries[table])

    def read(self, table: str, size: int) -> list[tuple[Any, ...]]:
        return [self._row(table, row) for row in self.connection.fetchmany(size)]

    def _row(self, table: str, row: tuple[Any, ...]) -> tuple[Any, ...]:
        if table == "procurement_lots":
            lot, procedure, name, subject, price, smp, customer, platform, published = row
            return (
                lot,
                procedure,
                "",
                name,
                subject,
                price,
                None if smp is None else int(smp),
                customer,
                None,
                platform,
                1,
                0,
                published,
                self.index_id,
                self.before,
            )
        if table == "lot_participations":
            lot, inn, winner, status = row
            return lot, inn, "", supplier_id(inn, UUID(int=0), ""), int(winner), 1, 0, status
        lot, name, code = row
        key = hashlib.sha256(json.dumps([lot, name, code], ensure_ascii=False).encode()).hexdigest()
        return (
            uuid5(NAMESPACE, "procurement-item:" + key),
            lot,
            key,
            name,
            code,
            "unknown",
            {},
            None,
            "",
            None,
            "unmatched",
            None,
            "",
            "",
            1,
            0,
        )
