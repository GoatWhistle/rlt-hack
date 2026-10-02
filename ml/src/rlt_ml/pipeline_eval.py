"""Оценка полного конвейера через HTTP API на фиксированной выборке (D2).

Вход — JSONL с закупками: `lot_id`, `text`, `winner_inn`, `participant_inns`,
необязательные `category`, `history_lots`. Каждая закупка отправляется в
`POST /api/searches` как есть. Пропуск победителя на этапе поиска, ошибка и
пустой ответ считаются промахом и остаются в знаменателе.
"""

import argparse
import hashlib
import json
import random
import statistics
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

TIMEOUT_SECONDS = 30.0
BOOTSTRAP_ROUNDS = 2000
SEED = 42


@dataclass(frozen=True)
class Case:
    lot_id: str
    text: str
    winner_inn: str
    participant_inns: tuple[str, ...] = ()
    category: str = ""
    history_lots: int = 0
    categories: tuple[str, ...] = ()

    @property
    def length(self) -> str:
        words = len(self.text.split())
        return "short" if words <= 4 else "long"

    @property
    def multi(self) -> str:
        return "multi" if ";" in self.text or "\n" in self.text else "single"

    @property
    def history(self) -> str:
        if self.history_lots == 0:
            return "none"
        return "small" if self.history_lots < 10 else "large"


@dataclass
class Outcome:
    case: Case
    ranked: list[str] = field(default_factory=list)
    error: str = ""
    seconds: float = 0.0

    def rank_of(self, inn: str) -> int | None:
        return self.ranked.index(inn) + 1 if inn in self.ranked else None


def read_cases(path: Path) -> list[Case]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cases.append(
            Case(
                lot_id=str(row["lot_id"]),
                text=str(row["text"]),
                winner_inn=str(row["winner_inn"]),
                participant_inns=tuple(str(inn) for inn in row.get("participant_inns", ())),
                category=str(row.get("category", "")),
                history_lots=int(row.get("history_lots", 0)),
                categories=tuple(str(value) for value in row.get("categories", ())),
            )
        )
    return cases


def sample_hash(cases: Sequence[Case]) -> str:
    joined = "\n".join(sorted(case.lot_id for case in cases))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


Searcher = Callable[[str], list[str]]


def http_searcher(base_url: str, limit: int) -> Searcher:
    def search(text: str) -> list[str]:
        body = json.dumps({"text": text, "limit": limit}).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/searches",
            data=body,
            headers={"Content-Type": "application/json", "Accept-Language": "ru"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())
        return [candidate["inn"] for candidate in payload["candidates"] if candidate["inn"]]

    return search


def run(cases: Iterable[Case], search: Searcher) -> list[Outcome]:
    outcomes = []
    for case in cases:
        started = time.perf_counter()
        try:
            ranked = search(case.text)
            outcomes.append(Outcome(case, ranked, seconds=time.perf_counter() - started))
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as error:
            outcome = Outcome(case, error=type(error).__name__)
            outcome.seconds = time.perf_counter() - started
            outcomes.append(outcome)
    return outcomes


def metrics(outcomes: Sequence[Outcome]) -> dict[str, float | int]:
    total = len(outcomes)
    if total == 0:
        return {"queries": 0}
    ranks = [outcome.rank_of(outcome.case.winner_inn) for outcome in outcomes]
    recalls = []
    for outcome in outcomes:
        known = set(outcome.case.participant_inns) | {outcome.case.winner_inn}
        found = known & set(outcome.ranked[:10])
        recalls.append(len(found) / len(known))
    return {
        "queries": total,
        "winner_hit_1": sum(rank == 1 for rank in ranks) / total,
        "winner_hit_10": sum(rank is not None and rank <= 10 for rank in ranks) / total,
        "winner_in_pool": sum(rank is not None for rank in ranks) / total,
        "winner_mrr": sum(1 / rank for rank in ranks if rank) / total,
        "participant_recall_10": sum(recalls) / total,
        "errors": sum(bool(outcome.error) for outcome in outcomes) / total,
        "empty": sum(not outcome.error and not outcome.ranked for outcome in outcomes) / total,
    }


def bootstrap_mrr_delta(
    baseline: Sequence[Outcome], system: Sequence[Outcome], rounds: int = BOOTSTRAP_ROUNDS
) -> dict[str, float]:
    def reciprocal(outcome: Outcome) -> float:
        rank = outcome.rank_of(outcome.case.winner_inn)
        return 1 / rank if rank else 0.0

    pairs = [(reciprocal(a), reciprocal(b)) for a, b in zip(baseline, system, strict=True)]
    if not pairs:
        return {"delta": 0.0, "low": 0.0, "high": 0.0}
    rng = random.Random(SEED)
    deltas = []
    for _ in range(rounds):
        drawn = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        deltas.append(statistics.fmean(b - a for a, b in drawn))
    deltas.sort()
    return {
        "delta": statistics.fmean(b - a for a, b in pairs),
        "low": deltas[int(0.025 * rounds)],
        "high": deltas[int(0.975 * rounds) - 1],
    }


def slices(outcomes: Sequence[Outcome]) -> dict[str, dict[str, dict[str, float | int]]]:
    groups: dict[str, Callable[[Case], str]] = {
        "length": lambda case: case.length,
        "items": lambda case: case.multi,
        "history": lambda case: case.history,
    }
    report: dict[str, dict[str, dict[str, float | int]]] = {}
    for name, key in groups.items():
        buckets: dict[str, list[Outcome]] = {}
        for outcome in outcomes:
            buckets.setdefault(key(outcome.case), []).append(outcome)
        report[name] = {value: metrics(items) for value, items in sorted(buckets.items())}
    category_buckets: dict[str, list[Outcome]] = {}
    for outcome in outcomes:
        categories = outcome.case.categories or ((outcome.case.category or "unknown"),)
        for category in categories:
            category_buckets.setdefault(category, []).append(outcome)
    report["category"] = {
        value: metrics(items) for value, items in sorted(category_buckets.items())
    }
    return report


def latency(outcomes: Sequence[Outcome]) -> dict[str, float]:
    times = sorted(outcome.seconds for outcome in outcomes)
    if not times:
        return {}
    return {
        "p50": times[len(times) // 2],
        "p95": times[min(len(times) - 1, int(0.95 * len(times)))],
    }


def report(cases: Sequence[Case], baseline: Sequence[Outcome], system: Sequence[Outcome]) -> dict:
    return {
        "sample_sha256": sample_hash(cases),
        "queries": len(cases),
        "baseline": metrics(baseline),
        "system": metrics(system),
        "winner_mrr_delta": bootstrap_mrr_delta(baseline, system),
        "system_slices": slices(system),
        "system_latency_seconds": latency(system),
        "rules": "errors and empty answers stay in the denominator; retrieval misses are misses",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--baseline-url", required=True)
    parser.add_argument("--system-url", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    cases = read_cases(arguments.cases)
    baseline = run(cases, http_searcher(arguments.baseline_url, arguments.limit))
    system = run(cases, http_searcher(arguments.system_url, arguments.limit))
    arguments.out.write_text(
        json.dumps(report(cases, baseline, system), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
