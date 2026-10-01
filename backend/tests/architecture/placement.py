import ast
from pathlib import PurePosixPath

from tests.architecture.rules import SourceFile, Violation, imported_modules

ERROR_BASES = frozenset({"Exception", "ValueError", "RuntimeError", "LookupError", "TypeError"})
CONTEXT_EXCEPTIONS = frozenset({("classifier", "normalizer")})
SHARED_SERVICE_MODULES = frozenset({"errors"})
SQL_BOUNDARY = (
    "src/adapter/repository/clickhouse/pool/",
    "src/adapter/repository/clickhouse/upload_store/rows.py",
    "src/adapter/repository/clickhouse/upload_store/store.py",
    "src/application/deferred_gateway.py",
)


def _base_names(node: ast.ClassDef) -> list[str]:
    names: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
        elif isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name):
            names.append(base.value.id)
    return names


def _classes(file: SourceFile) -> list[ast.ClassDef]:
    return [node for node in ast.walk(ast.parse(file.text)) if isinstance(node, ast.ClassDef)]


def _file_name(file: SourceFile) -> str:
    return PurePosixPath(file.path).name


def protocols_location(file: SourceFile) -> list[Violation]:
    if _file_name(file) == "protocols.py":
        return []
    return [
        Violation(file.path, node.lineno, "protocols-location")
        for node in _classes(file)
        if "Protocol" in _base_names(node)
    ]


def _is_error(node: ast.ClassDef) -> bool:
    return any(name in ERROR_BASES or name.endswith("Error") for name in _base_names(node))


def errors_location(file: SourceFile) -> list[Violation]:
    if _file_name(file) == "errors.py":
        return []
    return [
        Violation(file.path, node.lineno, "errors-location")
        for node in _classes(file)
        if _is_error(node)
    ]


def _context(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) < 3 or parts[:2] != ["src", "service"]:
        return None
    return parts[2]


def service_context(file: SourceFile) -> list[Violation]:
    own = _context(file.module)
    if own is None:
        return []
    found: list[Violation] = []
    for line, module in imported_modules(file):
        other = _context(module)
        if other is None or other in (own, *SHARED_SERVICE_MODULES):
            continue
        if (own, other) not in CONTEXT_EXCEPTIONS:
            found.append(Violation(file.path, line, f"service-context:{module}"))
    return found


def no_any(file: SourceFile) -> list[Violation]:
    if not file.path.startswith("src/") or file.path.startswith(SQL_BOUNDARY):
        return []
    return [
        Violation(file.path, node.lineno, "no-any")
        for node in ast.walk(ast.parse(file.text))
        if isinstance(node, ast.ImportFrom)
        and node.module == "typing"
        and any(alias.name == "Any" for alias in node.names)
    ]


PLACEMENT_RULES = (protocols_location, errors_location, service_context)
