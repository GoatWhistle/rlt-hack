from urllib.parse import urlsplit

from src.controller.uploads.evidence import explanation, purchases
from src.models.upload import LotRecommendation, Upload


def safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in {"https", "http"} and parsed.hostname else ""
    except ValueError:
        return ""


def profile_summary(profile: str) -> str:
    text = " ".join(profile.split())
    return text if len(text) <= 650 else text[:650].rsplit(" ", 1)[0] + "…"


def lot_summary(lot: LotRecommendation) -> dict:
    return {
        "id": lot.notice.lot_id,
        "title": lot.notice.title,
        "subject": lot.notice.subject,
        "customerInn": lot.notice.customer_inn or None,
        "deliveryRegion": lot.notice.delivery_region or None,
        "startPrice": float(lot.notice.start_price) if lot.notice.start_price is not None else None,
        "status": "ready" if lot.candidates else "noCandidates",
        "products": 0,
        "candidates": len(lot.candidates),
    }


def summary(upload: Upload) -> dict:
    found = sum(bool(lot.candidates) for lot in upload.lots)
    return {
        "id": upload.upload_id,
        "fileName": upload.filename,
        "createdAt": upload.created_at,
        "total": len(upload.lots),
        "processed": len(upload.lots),
        "counts": {
            "ready": found,
            "needsCheck": 0,
            "noCandidates": len(upload.lots) - found,
            "failed": 0,
        },
        "rejected": 0,
        "stored": True,
    }


def detail(upload: Upload) -> dict:
    return {**summary(upload), "lots": [lot_summary(lot) for lot in upload.lots], "issues": []}


def result(upload: Upload, lot: LotRecommendation) -> dict:
    return {
        "lot": lot_summary(lot),
        "recommendation": {
            "fileName": upload.filename,
            "requestTitle": lot.notice.title,
            "lotLabel": lot.notice.lot_id,
            "products": [],
            "companies": [
                {
                    "id": candidate.inn,
                    "name": candidate.name or f"Поставщик ИНН {candidate.inn}",
                    "inn": candidate.inn,
                    "role": candidate.category_name or f"ОКПД2 {candidate.category}",
                    "status": "recommended" if candidate.purchases else "historical",
                    "summary": explanation(candidate)
                    or profile_summary(
                        candidate.history_examples[0]
                        if candidate.history_examples
                        else candidate.profile
                    ),
                    "history": {
                        "category": candidate.category,
                        "examples": candidate.history_examples or candidate.profile.splitlines(),
                        "lastDate": candidate.history_last_date,
                    },
                    "contacts": {
                        "site": safe_url(candidate.website),
                        "email": candidate.email,
                        "phone": candidate.phone,
                    },
                    "catalog": [
                        {
                            "name": item.name,
                            "url": safe_url(item.url),
                            "checkedAt": item.observed_at,
                        }
                        for item in candidate.catalog
                        if safe_url(item.url)
                    ],
                    "identitySource": safe_url(candidate.identity_url),
                    "rankingReasons": candidate.ranking_reasons,
                    "registeredRegion": candidate.registered_region,
                    "matches": [],
                    "similarPurchases": candidate.category_lots,
                    "wins": candidate.category_wins,
                    "purchases": purchases(upload, lot, candidate),
                    "clarify": [
                        "Уточните текущий ассортимент, наличие и условия поставки.",
                    ],
                }
                for candidate in lot.candidates
            ],
        },
    }
