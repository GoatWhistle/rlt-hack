from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
LAUNCHERS = (
    BACKEND / "Dockerfile",
    BACKEND.parent / "docker-compose.yml",
    BACKEND.parent / "deploy" / "compose.production.yml",
)


@pytest.mark.parametrize("path", LAUNCHERS, ids=lambda path: path.name)
def test_api_runs_in_a_single_process(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path.name} is outside the mounted tree")
    assert "--workers" not in path.read_text(encoding="utf-8")
