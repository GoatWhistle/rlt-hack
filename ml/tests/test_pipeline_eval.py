import json
from pathlib import Path

from rlt_ml.pipeline_eval import Case, bootstrap_mrr_delta, metrics, read_cases, report, run

CASES = [
    Case("1", "бумага офисная", "7801234564", ("7707083893",), "17.12", 0),
    Case("2", "крупа гречневая; рис", "7707083893", (), "10.61", 12),
    Case("3", "кабель", "7736050003", (), "27.32", 3),
]


def searcher(answers: dict[str, list[str] | Exception]):
    def search(text: str) -> list[str]:
        answer = answers[text]
        if isinstance(answer, Exception):
            raise answer
        return answer

    return search


def test_misses_errors_and_empty_answers_stay_in_the_denominator() -> None:
    outcomes = run(
        CASES,
        searcher(
            {
                "бумага офисная": ["7707083893", "7801234564"],
                "крупа гречневая; рис": TimeoutError(),
                "кабель": [],
            }
        ),
    )
    found = metrics(outcomes)
    assert found["queries"] == 3
    assert found["winner_mrr"] == 0.5 / 3
    assert found["winner_hit_10"] == 1 / 3
    assert (found["errors"], found["empty"]) == (1 / 3, 1 / 3)
    assert found["participant_recall_10"] == 1 / 3


def test_report_has_paired_delta_slices_and_a_fixed_sample(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(
                {
                    "lot_id": case.lot_id,
                    "text": case.text,
                    "winner_inn": case.winner_inn,
                    "participant_inns": list(case.participant_inns),
                    "category": case.category,
                    "history_lots": case.history_lots,
                }
            )
            for case in CASES
        ),
        encoding="utf-8",
    )
    cases = read_cases(path)
    assert cases == CASES
    base = run(cases, searcher({case.text: [] for case in cases}))
    system = run(cases, searcher({case.text: [case.winner_inn] for case in cases}))
    result = report(cases, base, system)
    assert result["winner_mrr_delta"]["delta"] == 1.0
    assert result["winner_mrr_delta"]["low"] == 1.0
    assert set(result["system_slices"]) == {"category", "length", "items", "history"}
    assert result["system_slices"]["items"]["multi"]["queries"] == 1
    assert len(result["sample_sha256"]) == 64
    assert bootstrap_mrr_delta([], [])["delta"] == 0.0
