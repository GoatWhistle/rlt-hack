import json

import pytest

from rlt_ml.common import sha256
from rlt_ml.reranking.context_export import export_context


@pytest.fixture
def artifacts(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    model = runtime / "ranker.cbm"
    model.write_bytes(b"synthetic-model")
    (runtime / "runtime.json").write_text(json.dumps({"files": {"ranker.cbm": sha256(model)}}))
    statistics = tmp_path / "customer_stats.parquet"
    statistics.write_bytes(b"synthetic-statistics")
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "passed": True,
                "mode": "metadata",
                "model_sha256": sha256(model),
                "customer_stats_sha256": sha256(statistics),
            }
        )
    )
    return runtime, statistics, report, tmp_path / "export"


def test_exports_verified_context(artifacts):
    runtime, statistics, report, out = artifacts
    export_context(*artifacts)
    manifest = json.loads((out / "runtime.json").read_text())
    assert manifest["files"]["customer_stats.parquet"] == sha256(statistics)
    assert (out / "ranker.cbm").read_bytes() == (runtime / "ranker.cbm").read_bytes()
    assert manifest["serving_verification"] == json.loads(report.read_text())
    with pytest.raises(FileExistsError):
        export_context(*artifacts)


@pytest.mark.parametrize(
    "field,value",
    [
        ("passed", False),
        ("mode", "text"),
        ("model_sha256", "wrong"),
        ("customer_stats_sha256", "wrong"),
    ],
)
def test_rejects_unverified_context(artifacts, field, value):
    report = artifacts[2]
    data = json.loads(report.read_text())
    data[field] = value
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        export_context(*artifacts)
    assert not artifacts[3].exists()


def test_rejects_corrupted_model(artifacts):
    (artifacts[0] / "ranker.cbm").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Invalid runtime artifact"):
        export_context(*artifacts)
