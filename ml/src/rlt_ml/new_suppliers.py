"""Экспертная проверка новых поставщиков (D3).

`select` отправляет запросы набора в API и пишет лист разметки: до пяти
кандидатов с `novelty = new` на запрос, запросы без новых кандидатов тоже
попадают в лист. `aggregate` считает доли по размеченному листу.
"""

import argparse
import csv
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

PER_QUERY = 5
LABELS = ("fits", "after_clarification", "does_not_fit", "insufficient")
CHECKS = ("identity_ok", "novelty_ok", "product_ok", "requirements_ok", "link_ok", "role_ok")
COLUMNS = (
    "query_id",
    "category",
    "query",
    "rank",
    "inn",
    "name",
    "offer",
    "url",
    "observed_at",
    "system_status",
    *CHECKS,
    "label",
    "rationale",
    "reviewer",
)

Searcher = Callable[[str], dict]


def http_searcher(base_url: str) -> Searcher:
    def search(text: str) -> dict:
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/searches",
            data=json.dumps({"text": text, "limit": 50}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())

    return search


def sheet_rows(queries: Sequence[dict], search: Searcher) -> list[dict]:
    rows = []
    for query in queries:
        base = {"query_id": query["id"], "category": query["category"], "query": query["text"]}
        try:
            result = search(query["text"])
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as error:
            rows.append(
                {
                    **base,
                    "system_status": f"error:{type(error).__name__}",
                    "rationale": "search failed",
                }
            )
            continue
        if not result.get("pipeline", {}).get("noveltySet"):
            raise ValueError("search API does not provide the archive novelty set")
        new = [item for item in result["candidates"] if item.get("novelty") == "new"]
        if not new:
            rows.append({**base, "rank": "", "label": "", "rationale": "no new candidates"})
        for candidate in new[:PER_QUERY]:
            offer = next((m["offer"] for m in candidate["matches"] if m.get("offer")), None) or {}
            rows.append(
                {
                    **base,
                    "rank": candidate["rank"],
                    "inn": candidate["inn"],
                    "name": candidate["name"],
                    "offer": offer.get("name", ""),
                    "url": offer.get("url", ""),
                    "observed_at": offer.get("observedAt", ""),
                    "system_status": candidate["status"],
                }
            )
    return rows


def write_sheet(path: Path, rows: Sequence[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, restval="")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: Sequence[dict]) -> dict:
    reviewed = [row for row in rows if row.get("rank")]
    queries = {row["query_id"] for row in rows}
    error_queries = {
        row["query_id"] for row in rows if str(row.get("system_status", "")).startswith("error:")
    }
    with_fit = {row["query_id"] for row in reviewed if row.get("label") == "fits"}
    total = len(reviewed)

    def share(predicate: Callable[[dict], bool]) -> float:
        return sum(predicate(row) for row in reviewed) / total if total else 0.0

    return {
        "queries": len(queries),
        "categories": len({row["category"] for row in rows}),
        "candidates": total,
        "error_queries": len(error_queries),
        "queries_with_suitable_new": len(with_fit) / len(queries) if queries else 0.0,
        "labels": {
            label: share(lambda row, label=label: row.get("label") == label) for label in LABELS
        },
        "false_confirmations": share(
            lambda row: (
                row.get("system_status") == "recommended"
                and row.get("label") in ("does_not_fit", "insufficient")
            )
        ),
        "broken_evidence": share(lambda row: row.get("link_ok") == "no"),
        "unknown_fields": share(lambda row: any(row.get(check) == "unknown" for check in CHECKS)),
        "unlabelled": share(lambda row: row.get("label") not in LABELS),
        "reviewers": len({row.get("reviewer") for row in reviewed if row.get("reviewer")}),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select")
    select.add_argument("--queries", type=Path, required=True)
    select.add_argument("--api", required=True)
    select.add_argument("--out", type=Path, required=True)
    summary = commands.add_parser("aggregate")
    summary.add_argument("--sheet", type=Path, required=True)
    summary.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.command == "select":
        lines = arguments.queries.read_text(encoding="utf-8").splitlines()
        queries = [json.loads(line) for line in lines if line.strip()]
        write_sheet(arguments.out, sheet_rows(queries, http_searcher(arguments.api)))
        return 0
    with arguments.sheet.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    arguments.out.write_text(json.dumps(aggregate(rows), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
