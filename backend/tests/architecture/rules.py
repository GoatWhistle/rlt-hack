import ast
import io
import sys
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
MAX_LINES = 250
MAX_FUNCTION_LINES = 40

CLEAN_ROOTS = (
    "src/models/errors.py",
    "src/models/search.py",
    "src/models/query_item.py",
    "src/models/evidence.py",
    "src/models/scoring.py",
    "src/models/retrieval.py",
    "src/models/offer_evidence.py",
    "src/models/purchase.py",
    "src/models/candidate.py",
    "src/models/search_result.py",
    "src/models/supplier_profile.py",
    "src/models/health.py",
    "src/models/procurement.py",
    "src/models/lot_result.py",
    "src/models/upload.py",
    "src/service/supplier_search",
    "src/service/supplier_profile",
    "src/service/health",
    "src/service/procurement_upload",
    "src/controller/http",
    "src/controller/search",
    "src/controller/supplier",
    "src/controller/health",
    "src/controller/api",
    "src/controller/upload",
    "src/controller/errors.py",
    "src/adapter/text",
    "src/adapter/system",
    "src/adapter/client",
    "src/adapter/file",
    "src/adapter/repository/clickhouse/retrieval",
    "src/adapter/repository/clickhouse/offer_search",
    "src/adapter/repository/clickhouse/history_search",
    "src/adapter/repository/clickhouse/supplier_read",
    "src/adapter/repository/clickhouse/offer_read",
    "src/adapter/repository/clickhouse/participation",
    "src/adapter/repository/clickhouse/search_archive",
    "src/adapter/repository/clickhouse/probe",
    "src/adapter/repository/clickhouse/upload_store",
    "src/adapter/repository/clickhouse/pool",
    "src/application/api.py",
    "src/application/deferred_gateway.py",
    "tests/architecture",
    "tests/models",
    "tests/service",
    "tests/adapter",
    "tests/controller",
    "tests/application",
    "tests/fakes",
    "tests/conftest.py",
    "bench",
)

ENTRY_POINT_IMPORTS = ("src.models", "src.controller", "src.service.errors", "src.application")

LAYER_IMPORTS = {
    "src.models": ("src.models",),
    "src.service": ("src.models", "src.service"),
    "src.controller.api": ENTRY_POINT_IMPORTS,
    "src.controller.job": ENTRY_POINT_IMPORTS,
    "src.controller": ("src.models", "src.controller", "src.service.errors"),
    "src.adapter": ("src.models", "src.adapter"),
}

STDLIB_ONLY = ("src.models", "src.service")


@dataclass(frozen=True, slots=True)
class Violation:
    path: str
    line: int
    rule: str


@dataclass(frozen=True, slots=True)
class SourceFile:
    path: str
    text: str

    @property
    def module(self) -> str:
        return self.path.removesuffix(".py").removesuffix("/__init__").replace("/", ".")


def source_files(roots: tuple[str, ...] = ("src", "tests")) -> Iterator[SourceFile]:
    for root in roots:
        base = BACKEND / root
        paths = [base] if base.is_file() else sorted(base.rglob("*.py"))
        for path in paths:
            relative = path.relative_to(BACKEND).as_posix()
            yield SourceFile(relative, path.read_text(encoding="utf-8"))


def clean_files() -> Iterator[SourceFile]:
    roots = tuple(root for root in CLEAN_ROOTS if (BACKEND / root).exists())
    yield from source_files(roots)


def comments(file: SourceFile) -> list[Violation]:
    tokens = tokenize.generate_tokens(io.StringIO(file.text).readline)
    return [
        Violation(file.path, token.start[0], "comment")
        for token in tokens
        if token.type == tokenize.COMMENT
    ]


DOCUMENTED = ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


def leading_string(body: list[ast.stmt]) -> ast.stmt | None:
    first = body[0] if body else None
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        return first if isinstance(first.value.value, str) else None
    return None


def docstrings(file: SourceFile) -> list[Violation]:
    found: list[Violation] = []
    for node in ast.walk(ast.parse(file.text)):
        string = leading_string(node.body) if isinstance(node, DOCUMENTED) else None
        if string is not None:
            found.append(Violation(file.path, string.lineno, "docstring"))
    return found


def nested_imports(file: SourceFile) -> list[Violation]:
    tree = ast.parse(file.text)
    found: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Import | ast.ImportFrom):
                    found.append(Violation(file.path, inner.lineno, "nested-import"))
    return found


def relative_imports(file: SourceFile) -> list[Violation]:
    return [
        Violation(file.path, node.lineno, "relative-import")
        for node in ast.walk(ast.parse(file.text))
        if isinstance(node, ast.ImportFrom) and node.level > 0
    ]


def length(file: SourceFile) -> list[Violation]:
    lines = file.text.count("\n")
    return [Violation(file.path, lines, "file-length")] if lines > MAX_LINES else []


def function_length(file: SourceFile) -> list[Violation]:
    found: list[Violation] = []
    for node in ast.walk(ast.parse(file.text)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            span = (node.end_lineno or node.lineno) - node.lineno + 1
            if span > MAX_FUNCTION_LINES:
                found.append(Violation(file.path, node.lineno, "function-length"))
    return found


def imported_modules(file: SourceFile) -> Iterator[tuple[int, str]]:
    for node in ast.walk(ast.parse(file.text)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.lineno, node.module


def layer_of(module: str) -> str | None:
    return next((layer for layer in LAYER_IMPORTS if module.startswith(layer)), None)


def layering(file: SourceFile) -> list[Violation]:
    layer = layer_of(file.module)
    if layer is None:
        return []
    allowed = LAYER_IMPORTS[layer]
    stdlib_only = layer in STDLIB_ONLY
    found: list[Violation] = []
    for line, module in imported_modules(file):
        internal = module.startswith("src.")
        if internal and not module.startswith(allowed):
            found.append(Violation(file.path, line, f"layer:{module}"))
        elif not internal and stdlib_only and not is_stdlib(module):
            found.append(Violation(file.path, line, f"dependency:{module}"))
    return found


def is_stdlib(module: str) -> bool:
    return module.partition(".")[0] in sys.stdlib_module_names


CLEAN_RULES = (comments, docstrings, nested_imports, relative_imports, length, function_length)
