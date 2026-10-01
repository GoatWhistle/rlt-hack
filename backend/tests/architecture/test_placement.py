import pytest

from tests.architecture.placement import (
    PLACEMENT_RULES,
    errors_location,
    no_any,
    protocols_location,
    service_context,
)
from tests.architecture.rules import SourceFile, clean_files, source_files


def snippet(text: str, path: str = "src/service/a/sample.py") -> SourceFile:
    return SourceFile(path, text)


def test_protocols_live_only_in_protocols_modules() -> None:
    declared = "from typing import Protocol\nclass Port(Protocol):\n    pass\n"
    assert [item.rule for item in protocols_location(snippet(declared))] == ["protocols-location"]
    assert protocols_location(snippet(declared, "src/service/a/protocols.py")) == []


def test_errors_live_only_in_errors_modules() -> None:
    declared = "class BrokenError(ValueError):\n    pass\nclass Plain:\n    pass\n"
    assert [item.line for item in errors_location(snippet(declared))] == [1]
    assert errors_location(snippet(declared, "src/service/errors.py")) == []


@pytest.mark.parametrize(
    ("path", "statement", "found"),
    [
        ("src/service/a/x.py", "from src.service.b.y import z", True),
        ("src/service/a/x.py", "from src.service.a.y import z", False),
        ("src/service/a/x.py", "from src.service.errors import z", False),
        ("src/service/a/x.py", "from src.models.y import z", False),
        ("src/service/classifier/x.py", "from src.service.normalizer.text import z", False),
        ("src/controller/a/x.py", "from src.service.errors import z", False),
    ],
)
def test_service_contexts_stay_apart(path: str, statement: str, found: bool) -> None:
    assert bool(service_context(snippet(f"{statement}\n", path))) is found


def test_any_is_kept_at_the_sql_boundary() -> None:
    typed = "from typing import Any\n"
    assert [item.rule for item in no_any(snippet(typed))] == ["no-any"]
    boundary = "src/adapter/repository/clickhouse/pool/gateway.py"
    assert no_any(snippet(typed, boundary)) == []
    assert no_any(snippet("from typing import Protocol\n")) == []


def test_the_whole_source_tree_respects_placement() -> None:
    found = [
        violation
        for file in source_files(("src",))
        for rule in PLACEMENT_RULES
        for violation in rule(file)
    ]
    assert found == []


def test_clean_code_avoids_any() -> None:
    found = [violation for file in clean_files() for violation in no_any(file)]
    assert found == []
