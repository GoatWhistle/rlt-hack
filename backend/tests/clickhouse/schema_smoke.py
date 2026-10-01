"""Проверка миграций и семантики обновлений на временной базе chDB."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from chdb.session import Session

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR, Migrator
from tests.clickhouse.chdb_gateway import ChdbGateway

REQUIRED_OBJECTS = {
    "schema_migrations",
    "suppliers",
    "suppliers_current",
    "sources",
    "sources_current",
    "crawl_runs",
    "offers",
    "offers_current",
    "catalog_items",
    "catalog_items_current",
    "offer_matches",
    "offer_matches_current",
    "embeddings",
    "embeddings_current",
    "procurement_lots",
    "procurement_lots_current",
    "procurement_items",
    "procurement_items_current",
    "lot_participations",
    "lot_participations_current",
    "searches",
    "searches_current",
}
SUPPLIERS_BY_CATALOG_ITEM = """
SELECT s.supplier_id, s.name, o.offer_id
FROM supplier_search.offer_matches_current AS m
INNER JOIN supplier_search.offers_current AS o
    ON o.offer_id = m.offer_id AND o.content_hash = m.offer_content_hash
INNER JOIN supplier_search.suppliers_current AS s ON s.supplier_id = o.supplier_id
WHERE m.status = 'accepted' AND m.catalog_item_id = toUUID('{item}')
"""
NEAREST_CATALOG_ITEMS = """
SELECT entity_id, cosineDistance(embedding, {vector}) AS distance
FROM supplier_search.embeddings_current
WHERE entity_type = 'catalog_item' AND model_key = '{model_key}'
    AND dimensions = length({vector})
ORDER BY distance, entity_id
LIMIT 10
"""


async def main():
    with tempfile.TemporaryDirectory(prefix="rlt-schema-") as tmp:
        session = Session(tmp)
        try:

            def execute(sql):
                return session.query(sql, "JSONEachRow")

            def rows(sql):
                return [json.loads(line) for line in str(execute(sql)).splitlines()]

            def insert(table, row):
                execute(
                    f"INSERT INTO supplier_search.{table} FORMAT JSONEachRow "
                    + json.dumps(row, ensure_ascii=False)
                )

            migrator = Migrator(ChdbGateway(session), MIGRATION_DIR)
            applied = await migrator.apply_pending()
            assert applied == sorted(path.name for path in MIGRATION_DIR.glob("*.sql"))
            # Повторный запуск не выполняет применённые файлы заново.
            assert await migrator.apply_pending() == []
            objects = rows("SELECT name FROM system.tables WHERE database = 'supplier_search'")
            missing = REQUIRED_OBJECTS - {row["name"] for row in objects}
            assert not missing, missing

            supplier = "00000000-0000-0000-0000-000000000001"
            offer = "00000000-0000-0000-0000-000000000002"
            first = "00000000-0000-0000-0000-000000000003"
            second = "00000000-0000-0000-0000-000000000004"
            source = "00000000-0000-0000-0000-000000000005"
            base = {
                "supplier_id": supplier,
                "inn": "0123456789",
                "name": "Поставщик",
                "identity_status": "verified",
                "version": 1,
            }
            insert("suppliers", base)
            insert("suppliers", dict(base, name="Новое имя", version=2))
            insert("suppliers", base)  # Поздняя доставка старой версии.
            state = rows("SELECT name, inn FROM supplier_search.suppliers_current")
            assert state == [{"name": "Новое имя", "inn": "0123456789"}]

            for item in (first, second):
                insert(
                    "catalog_items",
                    {
                        "catalog_item_id": item,
                        "name": "Бумага",
                        "status": "confirmed",
                        "item_type": "goods",
                        "version": 1,
                    },
                )
            proposal = {
                "offer_id": offer,
                "source_id": source,
                "supplier_id": supplier,
                "seller_status": "verified",
                "name": "Бумага А4",
                "url": "https://example.test/paper",
                "content_hash": "hash-1",
                "first_seen_at": "2026-10-01 10:00:00.000",
                "last_seen_at": "2026-10-01 10:00:00.000",
                "version": 1,
            }
            insert("offers", proposal)
            match = {
                "offer_id": offer,
                "catalog_item_id": first,
                "status": "accepted",
                "confidence": 0.9,
                "offer_content_hash": "hash-1",
                "version": 1,
            }
            insert("offer_matches", match)

            def find(item):
                return rows(SUPPLIERS_BY_CATALOG_ITEM.format(item=item))

            assert len(find(first)) == 1
            insert("offer_matches", dict(match, catalog_item_id=second, version=2))
            insert("offer_matches", match)
            assert find(first) == [] and len(find(second)) == 1
            insert("offers", dict(proposal, content_hash="hash-2", version=2))
            assert find(second) == []  # Старая нормализация не используется.
            insert("offers", dict(proposal, version=3, is_deleted=1))
            insert("offers", proposal)
            assert rows("SELECT offer_id FROM supplier_search.offers_current") == []

            vector = {
                "entity_type": "catalog_item",
                "entity_id": first,
                "model_key": "test-v1",
                "dimensions": 3,
                "embedding": [1.0, 0.0, 0.0],
                "version": 1,
            }
            insert("embeddings", vector)
            insert("embeddings", dict(vector, entity_id=second, embedding=[0.0, 1.0, 0.0]))
            for invalid in ([1.0, 0.0], [0.0, 0.0, 0.0]):
                try:
                    insert("embeddings", dict(vector, embedding=invalid, version=2))
                except Exception as exc:
                    assert "valid_vector" in str(exc), str(exc)
                else:
                    raise AssertionError("Некорректный вектор принят")
            found = rows(
                NEAREST_CATALOG_ITEMS.format(
                    vector="CAST([1, 0, 0], 'Array(Float32)')", model_key="test-v1"
                )
            )
            assert len(found) == 2 and found[0]["entity_id"] == first
            assert abs(found[0]["distance"]) < 1e-6

            # Повтор одного обхода не создаёт два события в журнале.
            run = {
                "run_id": first,
                "source_id": source,
                "started_at": "2026-10-01 10:00:00.000",
                "finished_at": "2026-10-01 10:05:00.000",
                "status": "success",
                "suppliers_extracted": 3,
                "offers_extracted": 12,
                "provider_name": "yml_feed",
                "version": 1,
            }
            insert("crawl_runs", run)
            insert("crawl_runs", run)
            assert len(rows("SELECT * FROM supplier_search.crawl_runs FINAL")) == 1
            engine = rows("SELECT version() AS version")[0]["version"]
            print(f"OK: ClickHouse {engine}; миграции, повторный запуск, версии,")
            print("удаление, исправление связи, устаревший хеш, векторы, журнал обхода.")
        finally:
            session.close()


if __name__ == "__main__":
    asyncio.run(main())
