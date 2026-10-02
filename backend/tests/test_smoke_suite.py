import runpy
from pathlib import Path

import pytest

SMOKES = (
    "embedding/smoke.py",
    "embedding/document_smoke.py",
    "embedding/batching_smoke.py",
    "embedding/inference_smoke.py",
    "search/smoke.py",
    "search/clickhouse_smoke.py",
    "search/history_smoke.py",
    "search/ranker_smoke.py",
    "search/metadata_smoke.py",
    "search/upload_refresh_smoke.py",
    "registry/registry_smoke.py",
    "registry/registry_store_smoke.py",
    "product/moscow_smoke.py",
    "product/worker_smoke.py",
)


@pytest.mark.parametrize("script", SMOKES)
def test_component_smoke(script: str) -> None:
    runpy.run_path(str(Path(__file__).parent / script), run_name="__main__")
