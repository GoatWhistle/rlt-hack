import pytest

from tests.architecture.rules import (
    CLEAN_RULES,
    SourceFile,
    Violation,
    clean_files,
    comments,
    docstrings,
    function_length,
    layering,
    length,
    nested_imports,
    relative_imports,
    source_files,
)


def snippet(text: str, path: str = "src/service/x/sample.py") -> SourceFile:
    return SourceFile(path, text)


def rules_of(found: list[Violation]) -> list[str]:
    return [violation.rule for violation in found]


def test_comments_are_found_but_strings_are_not() -> None:
    file = snippet('value = "# not a comment"\nother = 1  # a comment\n# alone\n')
    assert [violation.line for violation in comments(file)] == [2, 3]


def test_docstrings_are_found_on_modules_classes_and_functions() -> None:
    file = snippet('"""m"""\nclass A:\n    """c"""\n    def f(self) -> None:\n        """f"""\n')
    assert rules_of(docstrings(file)) == ["docstring"] * 3
    assert docstrings(snippet("class A:\n    value = 1\n")) == []


def test_imports_inside_functions_and_relative_imports_are_rejected() -> None:
    file = snippet("from . import a\ndef f() -> None:\n    import os\n")
    assert rules_of(nested_imports(file)) == ["nested-import"]
    assert rules_of(relative_imports(file)) == ["relative-import"]
    assert nested_imports(snippet("import os\n")) == []


def test_long_files_and_functions_are_rejected() -> None:
    body = "".join(f"    x{index} = {index}\n" for index in range(41))
    assert rules_of(function_length(snippet(f"def f() -> None:\n{body}"))) == ["function-length"]
    assert rules_of(length(snippet("x = 1\n" * 251))) == ["file-length"]
    assert length(snippet("x = 1\n" * 250)) == []


@pytest.mark.parametrize(
    ("path", "statement", "expected"),
    [
        ("src/service/a/b.py", "from src.adapter.text import x", ["layer:src.adapter.text"]),
        ("src/service/a/b.py", "import httpx", ["dependency:httpx"]),
        ("src/service/a/b.py", "import asyncio\nfrom src.models.search import x", []),
        ("src/models/a.py", "from src.service.errors import x", ["layer:src.service.errors"]),
        ("src/controller/a/b.py", "from src.adapter.text import x", ["layer:src.adapter.text"]),
        ("src/controller/a/b.py", "from src.service.errors import x", []),
        ("src/controller/api/main.py", "from src.application.container import x", []),
        ("src/adapter/a/b.py", "from src.service.errors import x", ["layer:src.service.errors"]),
    ],
)
def test_layers_import_only_downwards(path: str, statement: str, expected: list[str]) -> None:
    assert rules_of(layering(snippet(f"{statement}\n", path))) == expected


def test_new_code_has_no_comments_docstrings_or_local_imports() -> None:
    files = list(clean_files())
    assert len(files) > 10
    found = [violation for file in files for rule in CLEAN_RULES for violation in rule(file)]
    assert found == []


def test_every_layer_respects_its_boundaries() -> None:
    found = [violation for file in source_files(("src",)) for violation in layering(file)]
    assert found == []
