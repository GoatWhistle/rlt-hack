from urllib.parse import quote

from src.models.operations.upload import LotRecommendation, Upload
from src.models.search.supplier_search import SupplierCandidate


def purchases(upload: Upload, lot: LotRecommendation, candidate: SupplierCandidate) -> list[dict]:
    base = f"/uploads/{upload.upload_id}/lots/{quote(lot.notice.lot_id, safe='')}"
    return [
        {
            "title": item.title,
            "year": int(item.publish_date[:4]),
            "date": item.publish_date,
            "customerInn": item.customer_inn,
            "products": item.product_names,
            "outcome": "winner" if item.is_winner else "participant",
            "source": {
                "kind": "purchase",
                "title": f"Архив закупок · {item.source_system}",
                "url": f"{base}/evidence/{candidate.inn}/{quote(item.lot_id, safe='')}",
                "checkedAt": item.publish_date,
            },
        }
        for item in candidate.purchases
    ]


def position_matches(
    upload: Upload, lot: LotRecommendation, candidate: SupplierCandidate
) -> list[dict]:
    sources = {item.lot_id: item for item in candidate.purchases}
    base = f"/uploads/{upload.upload_id}/lots/{quote(lot.notice.lot_id, safe='')}"
    return [
        {
            "productId": position.item_id,
            "basis": "historical",
            "source": {
                "kind": "purchase",
                "title": sources[purchase_id].title,
                "url": f"{base}/evidence/{candidate.inn}/{quote(purchase_id, safe='')}",
                "checkedAt": sources[purchase_id].publish_date,
            },
        }
        for position in lot.notice.positions
        if (purchase_id := candidate.position_evidence.get(position.item_id)) in sources
    ]


def explanation(candidate: SupplierCandidate) -> str:
    if not candidate.purchases:
        return ""
    products = list(
        dict.fromkeys(name for item in candidate.purchases for name in item.product_names)
    )
    facts = (
        f"Закупок в категории {candidate.category} — {candidate.category_lots}"
        if candidate.category_lots is not None
        else f"Найдены закупки в категории {candidate.category}"
    )
    if candidate.category_wins:
        facts += f", подтверждённых побед — {candidate.category_wins}"
    facts += "."
    if products:
        facts += " В истории: " + "; ".join(products[:3])[:350] + "."
    return facts
