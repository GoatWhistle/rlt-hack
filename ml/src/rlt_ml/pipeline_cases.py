"""Новая независимая выборка закупок для оценки полного конвейера (D2).

Берутся процедуры позже границы истории индекса с однозначным победителем,
исключаются уже использованные для принятия модели (закрытый test).
Выборка детерминирована: seed и SHA256 списка пишутся рядом с файлом.
"""

import argparse
import hashlib
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import duckdb

SELECT_LOTS = """
SELECT l.lot_id,
       coalesce(nullif(l.procedure_name, ''), l.query_text) AS text,
       any_value(p.supplier_inn) FILTER (WHERE p.is_winner AND NOT p.label_conflict) AS winner,
       list(DISTINCT p.supplier_inn) AS participants,
       any_value(c.category) AS category
FROM lot_info l
JOIN participations p USING (lot_id)
LEFT JOIN lot_categories c USING (lot_id)
WHERE l.publish_date >= ? AND l.winner_count = 1 AND NOT l.notice_conflict
GROUP BY l.lot_id, text
HAVING winner IS NOT NULL AND length(text) > 0
ORDER BY hash(l.lot_id || ?), l.lot_id
"""


def build(
    connection: duckdb.DuckDBPyConnection,
    after: date,
    excluded: set[str],
    size: int,
    seed: int,
) -> list[dict]:
    rows = connection.execute(SELECT_LOTS, [after, str(seed)]).fetchall()
    cases = []
    for lot_id, text, winner, participants, category in rows:
        if str(lot_id) in excluded:
            continue
        cases.append(
            {
                "lot_id": str(lot_id),
                "text": str(text),
                "winner_inn": str(winner),
                "participant_inns": sorted(str(inn) for inn in participants if inn != winner),
                "category": str(category or ""),
            }
        )
        if len(cases) == size:
            break
    return cases


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--after", type=date.fromisoformat, required=True)
    parser.add_argument("--exclude", type=Path, help="список lot_id закрытого test, по строке")
    parser.add_argument("--size", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    excluded = set()
    if arguments.exclude:
        excluded = set(arguments.exclude.read_text(encoding="utf-8").split())
    with duckdb.connect(str(arguments.prepared), read_only=True) as connection:
        cases = build(connection, arguments.after, excluded, arguments.size, arguments.seed)
    lines = "\n".join(json.dumps(case, ensure_ascii=False) for case in cases)
    arguments.out.write_text(lines + "\n", encoding="utf-8")
    digest = hashlib.sha256("\n".join(sorted(c["lot_id"] for c in cases)).encode()).hexdigest()
    manifest = {
        "size": len(cases),
        "seed": arguments.seed,
        "after": str(arguments.after),
        "excluded": len(excluded),
        "sample_sha256": digest,
    }
    arguments.out.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
