from dataclasses import replace
from datetime import date

from src.adapter.repository.ranker.features import words
from src.adapter.repository.supplier_index.category_priority import requested_categories
from src.adapter.repository.supplier_index.protocols import SqlGateway
from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate, SupplierPurchase


async def enrich_archive_history(
    gateway: SqlGateway,
    database: str,
    index_id: str,
    before: date,
    text: str,
    context: SearchContext,
    candidates: list[SupplierCandidate],
) -> list[SupplierCandidate]:
    if not candidates:
        return []
    ready = await gateway.select(
        f"SELECT count() FROM {database}.procurement_archive_imports FINAL "
        "WHERE index_id={index:String} AND history_before={before:Date} AND status='completed'",
        {"index": index_id, "before": before},
    )
    if ready != [(1,)]:
        return candidates
    purchases: dict[str, list[SupplierPurchase]] = {}
    terms = sorted(words(text.replace("ё", "е").replace("-", " ")))[:128]
    for start in range(0, len(candidates), 10):
        batch = candidates[start : start + 10]
        rows = await gateway.select(
            _query(database),
            {
                "index": index_id,
                "before": before,
                "inns": [item.inn for item in batch],
                "codes": [code for code in context.okpd2_codes if code],
                "categories": sorted(requested_categories(context)),
                "terms": terms,
            },
        )
        for inn, lot, title, published, customer, system, products, winner in rows:
            purchases.setdefault(inn, []).append(
                SupplierPurchase(
                    lot,
                    title,
                    str(published)[:10],
                    customer or "",
                    system,
                    list(products),
                    bool(winner),
                )
            )
    return [
        replace(candidate, purchases=purchases.get(candidate.inn, [])) for candidate in candidates
    ]


def _query(database: str) -> str:
    return f"""
        WITH eligible AS (
            SELECT p.supplier_inn, p.lot_id,
                p.is_winner=1 AND p.winner_label_status='confirmed' AS winner,
                l.procedure_name, l.subject, l.publish_date, l.customer_inn, l.platform
            FROM (
                SELECT * FROM {database}.lot_participations_current
                WHERE supplier_inn IN {{inns:Array(String)}}
            ) p INNER JOIN (
                SELECT * FROM {database}.procurement_lots_current
                WHERE archive_index_id={{index:String}}
                  AND archive_history_before={{before:Date}} AND publish_date < {{before:Date}}
            ) l USING (lot_id)
        ), products AS (
            SELECT i.lot_id,
                uniqExactIf(i.okpd2_code, i.okpd2_code IN {{codes:Array(String)}}) AS exact_codes,
                uniqExactIf(left(i.okpd2_code, 5),
                    left(i.okpd2_code, 5) IN {{categories:Array(String)}}) AS categories,
                sum(length(arrayIntersect(
                    splitByRegexp('[^0-9a-zа-я]+', replaceAll(lowerUTF8(i.product_name), 'ё', 'е')),
                    {{terms:Array(String)}}))) AS text_matches,
                arrayDistinct(arrayConcat(
                    groupUniqArrayIf(100)(i.product_name, length(arrayIntersect(
                        splitByRegexp('[^0-9a-zа-я]+',
                            replaceAll(lowerUTF8(i.product_name), 'ё', 'е')),
                        {{terms:Array(String)}})) > 0),
                    groupUniqArray(100)(i.product_name))) AS names
            FROM {database}.procurement_items_current i
            INNER JOIN (SELECT DISTINCT lot_id FROM eligible) selected USING (lot_id)
            GROUP BY i.lot_id
        )
        SELECT supplier_inn, lot_id,
            if(procedure_name != '', procedure_name, subject) AS title,
            publish_date, ifNull(customer_inn, ''), platform, names, winner
        FROM eligible LEFT JOIN products USING (lot_id)
        WHERE exact_codes > 0 OR categories > 0 OR text_matches > 0
            OR length(arrayIntersect(
                splitByRegexp('[^0-9a-zа-я]+', replaceAll(lowerUTF8(title), 'ё', 'е')),
                {{terms:Array(String)}})) > 0
        ORDER BY exact_codes DESC, categories DESC, text_matches DESC,
            length(arrayIntersect(
                splitByRegexp('[^0-9a-zа-я]+', replaceAll(lowerUTF8(title), 'ё', 'е')),
                {{terms:Array(String)}})) DESC,
            publish_date DESC, winner DESC, lot_id
        LIMIT 5 BY supplier_inn
        SETTINGS max_threads=2, max_memory_usage=536870912,
            max_bytes_before_external_group_by=134217728,
            max_bytes_before_external_sort=134217728
    """
