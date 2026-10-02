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


def explanation(candidate: SupplierCandidate) -> str:
    if not candidate.purchases:
        return ""
    products = list(
        dict.fromkeys(name for item in candidate.purchases for name in item.product_names)
    )
    facts = f"Закупок в категории {candidate.category} — {candidate.category_lots}"
    if candidate.category_wins:
        facts += f", подтверждённых побед — {candidate.category_wins}"
    facts += "."
    if products:
        facts += " В истории: " + "; ".join(products[:3])[:350] + "."
    return facts
