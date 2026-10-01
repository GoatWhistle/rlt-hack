import json

from rlt_ml.compare_cards import compare


def test_comparison_is_paired_and_uses_procedure_clusters(tmp_path):
    common = [
        {"lot_id": "1", "procedure_group": "p1", "participants": ["a", "b"],
         "winner_inn": "a"},
        {"lot_id": "2", "procedure_group": "p1", "participants": ["b"],
         "winner_inn": "b"},
        {"lot_id": "3", "procedure_group": "p2", "participants": ["c"],
         "winner_inn": "c"},
    ]
    paths = {}
    for variant, hybrid, dense in [
        ("A", [["a"], ["b"], ["x"]], [["a"], ["x"], ["c"]]),
        ("B", [["a", "b"], ["b"], ["c"]], [["a", "b"], ["b"], ["c"]]),
    ]:
        path = tmp_path / f"{variant}.jsonl"
        with path.open("w") as handle:
            for row, candidates, dense_candidates in zip(common, hybrid, dense, strict=True):
                handle.write(json.dumps({**row, "candidate_inns": candidates,
                                         "dense_candidate_inns": dense_candidates}) + "\n")
        paths[variant] = path
    report = compare(paths, replicates=20, seed=7)
    assert report["procedure_groups"] == 2
    assert report["paired_deltas"]["hybrid"]["B"]["recall_at_100"]["delta"] > 0
    assert "dense_only" in report["paired_deltas"]


def test_comparison_rejects_different_queries(tmp_path):
    base = {"lot_id": "1", "procedure_group": "p1", "participants": ["a"],
            "winner_inn": "a", "candidate_inns": ["a"], "dense_candidate_inns": ["a"]}
    other = {**base, "lot_id": "2"}
    first, second = tmp_path / "A.jsonl", tmp_path / "B.jsonl"
    first.write_text(json.dumps(base) + "\n")
    second.write_text(json.dumps(other) + "\n")
    try:
        compare({"A": first, "B": second}, replicates=5)
    except ValueError as error:
        assert "запросов отличается" in str(error)
    else:
        raise AssertionError("Разные выборки запросов должны быть отклонены")
