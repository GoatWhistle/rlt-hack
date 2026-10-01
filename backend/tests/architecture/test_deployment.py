import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
REPOSITORY = BACKEND.parent
DOCKERFILE = BACKEND / "Dockerfile"
LAUNCHERS = (
    DOCKERFILE,
    REPOSITORY / "docker-compose.yml",
    REPOSITORY / "deploy" / "compose.production.yml",
)


def read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"{path.name} is outside the mounted tree")
    return path.read_text(encoding="utf-8")


def stage(dockerfile: str, name: str) -> str:
    match = re.search(rf"^FROM \S+ AS {name}$(.*?)(?=^FROM |\Z)", dockerfile, re.M | re.S)
    assert match is not None, name
    return match.group(1)


@pytest.mark.parametrize("path", LAUNCHERS, ids=lambda path: path.name)
def test_api_runs_in_a_single_process(path: Path) -> None:
    assert "--workers" not in read(path)


def test_api_image_runs_as_unprivileged_user() -> None:
    assert re.search(r"^USER api$", stage(read(DOCKERFILE), "api"), re.M)
    package = read(REPOSITORY / "deploy" / "package.sh")
    assert '--target api --tag "rlt/backend-api:$revision"' in package
    assert '--target job --tag "rlt/backend:$revision"' in package


def test_image_installs_locked_dependencies() -> None:
    base = stage(read(DOCKERFILE), "base")
    assert "COPY pyproject.toml uv.lock ./" in base
    assert "uv sync --frozen --no-dev" in base
    assert "pip install" not in base


def test_production_api_hides_docs_and_drops_privileges() -> None:
    production = read(REPOSITORY / "deploy" / "compose.production.yml")
    api = production.split("\n  frontend:", 1)[0]
    for setting in (
        "image: rlt/backend-api:",
        "API_DOCS: ${API_DOCS:-false}",
        "mem_limit:",
        "read_only: true",
        "cap_drop: [ALL]",
        "no-new-privileges:true",
    ):
        assert setting in api, setting


def test_api_healthcheck_uses_readiness() -> None:
    compose = read(REPOSITORY / "docker-compose.yml")
    api = compose.split("\n  api:\n", 1)[1].split("\n  backend-tests:", 1)[0]
    assert "/api/health/ready" in api
    assert "/api/health/live" not in api


def test_release_smoke_requires_a_successful_search() -> None:
    smoke = read(REPOSITORY / "deploy" / "smoke.sh")
    for check in ("$api/health/ready", "'.candidates | length'", "grep -qx 201", "/summary"):
        assert check in smoke, check


@pytest.mark.parametrize("path", LAUNCHERS[:2], ids=lambda path: path.name)
def test_api_command_uses_json_logging(path: Path) -> None:
    assert '"--log-config", "src/controller/api/logging.json"' in read(path)
    assert (BACKEND / "src" / "controller" / "api" / "logging.json").is_file()
