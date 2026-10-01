"""Восстановление полей пакета после очистки общей схемы ClickHouse."""

import sys
import tempfile
from pathlib import Path

from chdb.session import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR, split_statements


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="gisp-schema-") as directory:
        session = Session(directory)
        try:
            for name in (
                "0001_initial_schema.sql",
                "0002_parsing_job.sql",
                "0003_source_providers.sql",
            ):
                for statement in split_statements((MIGRATION_DIR / name).read_text()):
                    session.query(statement)
            for table, columns in (
                ("sources", ("enabled",)),
                ("suppliers", ("legal_status",)),
                ("offers", ("seller_evidence_url", "delivery_regions", "role_evidence_url")),
            ):
                session.query(f"DROP VIEW IF EXISTS supplier_search.{table}_current")
                if table == "sources":
                    session.query("ALTER TABLE supplier_search.sources DROP CONSTRAINT valid_flags")
                for column in columns:
                    session.query(f"ALTER TABLE supplier_search.{table} DROP COLUMN {column}")
            for statement in split_statements(
                (MIGRATION_DIR / "0011_restore_supplier_metadata.sql").read_text()
            ):
                session.query(statement)
            for table, expected in (
                ("sources", ("enabled",)),
                ("suppliers", ("legal_status",)),
                ("offers", ("seller_evidence_url", "delivery_regions", "role_evidence_url")),
            ):
                result = session.query(f"DESCRIBE TABLE supplier_search.{table}", "CSV")
                columns = {line.split(",", 1)[0].strip('"') for line in str(result).splitlines()}
                assert set(expected) <= columns, table
                view = session.query(f"DESCRIBE TABLE supplier_search.{table}_current", "CSV")
                view_columns = {line.split(",", 1)[0].strip('"') for line in str(view).splitlines()}
                assert set(expected) <= view_columns, table
        finally:
            session.cleanup()


if __name__ == "__main__":
    main()
    print("ГИСП schema: проверки прошли")
