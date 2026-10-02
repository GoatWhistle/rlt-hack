import re

import pytest

from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR
from src.adapter.repository.clickhouse.retrieval.prefixes import prefix_terms, term_count

FORWARD_FROM = "0013"


def migration(prefix: str) -> str:
    path = next(MIGRATION_DIR.glob(f"{prefix}_*.sql"))
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(("prefix", "column"), [("0013", "search_text"), ("0014", "text")])
def test_indexes_match_query_expressions(prefix: str, column: str) -> None:
    sql = migration(prefix)
    assert prefix_terms(column) in sql
    assert term_count(column) in sql


def test_new_migrations_replace_views_atomically() -> None:
    for path in sorted(MIGRATION_DIR.glob("*.sql")):
        if path.name < FORWARD_FROM:
            continue
        assert not re.search(r"DROP\s+VIEW", path.read_text(encoding="utf-8"), re.IGNORECASE)


def test_mutations_finish_before_migration_completes() -> None:
    for statement in migration("0013").split(";"):
        if "MATERIALIZE" in statement:
            assert "mutations_sync = 2" in statement
