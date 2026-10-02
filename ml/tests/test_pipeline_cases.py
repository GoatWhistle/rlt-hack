from datetime import date

import duckdb

from rlt_ml.pipeline_cases import build


def connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE lot_info (lot_id VARCHAR, publish_date DATE, winner_count INT, "
        "procedure_name VARCHAR, query_text VARCHAR, notice_conflict BOOLEAN)"
    )
    con.execute(
        "CREATE TABLE participations (lot_id VARCHAR, supplier_inn VARCHAR, "
        "is_winner BOOLEAN, label_conflict BOOLEAN)"
    )
    con.execute("CREATE TABLE lot_categories (lot_id VARCHAR, category VARCHAR)")
    con.execute(
        "INSERT INTO lot_info VALUES "
        "('old', DATE '2025-01-01', 1, 'Бумага', '', false),"
        "('new', DATE '2025-07-01', 1, '', 'Крупа', false),"
        "('two', DATE '2025-07-02', 2, 'Кабель', '', false),"
        "('test', DATE '2025-07-03', 1, 'Ручки', '', false)"
    )
    con.execute(
        "INSERT INTO participations VALUES "
        "('old','1',true,false),('new','2',true,false),('new','3',false,false),"
        "('two','4',true,false),('test','5',true,false)"
    )
    con.execute("INSERT INTO lot_categories VALUES ('new','10.61')")
    return con


def test_sample_is_after_the_cutoff_unambiguous_and_excludes_test() -> None:
    cases = build(connection(), date(2025, 6, 1), {"test"}, 10, 42)
    assert cases == [
        {
            "lot_id": "new",
            "text": "Крупа",
            "winner_inn": "2",
            "participant_inns": ["3"],
            "category": "10.61",
        }
    ]
