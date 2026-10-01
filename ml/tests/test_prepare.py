import shutil
import zipfile
from pathlib import Path

import duckdb
import pyarrow.parquet as parquet
import pytest

from rlt_ml.common import read_config, validate_splits
from rlt_ml.prepare import prepare, source_files


def test_history_is_temporal_and_deduplicated(prepared):
    out, report = prepared
    with duckdb.connect(str(out / "procurement.duckdb"), read_only=True) as con:
        assert con.execute("SELECT count(*) FROM participations WHERE lot_id='h1'").fetchone()[0] == 2
        assert con.execute("SELECT count(*) FROM products WHERE lot_id='h1'").fetchone()[0] == 1
    train_stats = parquet.read_table(out / "train/supplier_stats.parquet").to_pylist()
    first = next(r for r in train_stats if r["supplier_inn"] == "0000000001")
    assert first["participations"] == 2
    categories = parquet.read_table(out / "train/category_stats.parquet").to_pylist()
    paper = next(r for r in categories if r["supplier_inn"] == "0000000001" and r["category"] == "17.23")
    assert paper["distinct_lots"] == 1
    assert paper["participations"] == 0.5
    for split in report["splits"]:
        cards = parquet.read_table(out / split["name"] / "cards.parquet").to_pylist()
        assert all(str(c["profile_last_date"]) < split["history_before"] for c in cards)
        assert all("FUTURE_SECRET" not in c["profile_text"] for c in cards)
        assert all(c["example_count"] <= 5 for c in cards)
    assert report["quality"]["orphan_participations"] == 1


def test_ranker_excludes_ambiguous_labels_but_keeps_cold_start_targets(prepared):
    out, report = prepared
    for split in report["splits"]:
        folder = out / split["name"]
        ranker = parquet.read_table(folder / "ranker.parquet").to_pylist()
        assert len({r["lot_id"] for r in ranker}) == 4
        assert not any("ambiguous" in r["lot_id"] or "conflict" in r["lot_id"] for r in ranker)
        targets = parquet.read_table(folder / "targets.parquet").to_pylist()
        stats = parquet.read_table(folder / "supplier_stats.parquet").to_pylist()
        known_inns = {r["supplier_inn"] for r in stats}
        cold_targets = [r for r in targets if r["lot_id"].endswith("_new")]
        assert cold_targets and all(r["supplier_inn"] not in known_inns for r in cold_targets)
        queries = parquet.read_table(folder / "queries.parquet").to_pylist()
        assert not any(r["lot_id"].startswith("cross") for r in queries)
    assert report["splits"][0]["unseen_target_participations"] == 1


def test_encoder_uses_all_participants_and_only_single_product_lots(prepared):
    out, _ = prepared
    pairs = parquet.read_table(out / "train/encoder_pairs.parquet").to_pylist()
    assert {r["supplier_inn"] for r in pairs} == {"0000000001", "0000000002"}
    assert not any("missing" in r["lot_id"] for r in pairs)
    assert all("0000000003" in r["known_positive_inns"] for r in pairs)
    assert all(r["profile_text"] and r["query_text"] for r in pairs)


def test_repeated_run_cannot_overwrite(prepared, synthetic_source):
    out, _ = prepared
    config = Path(__file__).resolve().parents[1] / "configs/data.toml"
    with pytest.raises(FileExistsError):
        prepare(synthetic_source, out, config)


def test_config_rejects_gap_and_overlap():
    config = read_config(Path(__file__).resolve().parents[1] / "configs/data.toml")
    config["splits"][0]["history_before"] = "2024-06-25"
    with pytest.raises(ValueError, match="зазор"):
        validate_splits(config)


def test_lfs_pointer_is_not_a_dataset(tmp_path):
    (tmp_path / "Извещения.csv").write_text("version https://git-lfs.github.com/spec/v1\n")
    with pytest.raises(ValueError, match="указатель"):
        source_files(tmp_path, tmp_path / "raw")


def test_archive_extracts_expected_files_without_path_traversal(synthetic_source, tmp_path):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for path in synthetic_source.glob("*.csv"):
            z.write(path, "../../" + path.name)
        z.writestr("../../unexpected.txt", "ignored")
    files = source_files(archive, tmp_path / "raw")
    assert all(p.parent == tmp_path / "raw" for p in files.values())
    assert not (tmp_path / "unexpected.txt").exists()
    shutil.rmtree(tmp_path / "raw")
