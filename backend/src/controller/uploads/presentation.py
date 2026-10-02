from urllib.parse import urlsplit

from src.controller.uploads.evidence import explanation, position_matches, purchases
from src.models.operations.upload import LotRecommendation, Upload


def safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in {"https", "http"} and parsed.hostname else ""
    except ValueError:
        return ""


def profile_summary(profile: str) -> str:
    text = " ".join(profile.split())
    return text if len(text) <= 650 else text[:650].rsplit(" ", 1)[0] + "…"


def lot_status(lot: LotRecommendation) -> str:
    if not lot.processed:
        return "queued"
    if lot.failed:
        return "failed"
    return "ready" if lot.candidates else "noCandidates"


def lot_summary(lot: LotRecommendation) -> dict:
    return {
        "id": lot.notice.lot_id,
        "title": lot.notice.title,
        "subject": lot.notice.subject,
        "customerInn": lot.notice.customer_inn or None,
        "deliveryRegion": lot.notice.delivery_region or None,
        "startPrice": float(lot.notice.start_price) if lot.notice.start_price is not None else None,
        "status": lot_status(lot),
        "products": len(lot.notice.positions),
        "candidates": len(lot.candidates),
    }


def summary(upload: Upload) -> dict:
    processed = [lot for lot in upload.lots if lot.processed]
    failed = sum(lot.failed for lot in processed)
    found = sum(bool(lot.candidates) and not lot.failed for lot in processed)
    return {
        "id": upload.upload_id,
        "fileName": upload.filename,
        "title": upload.lots[0].notice.title if upload.lots else "",
        "createdAt": upload.created_at,
        "total": len(upload.lots),
        "processed": len(processed),
        "counts": {
            "ready": found,
            "needsCheck": 0,
            "noCandidates": len(processed) - found - failed,
            "failed": failed,
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
            "products": [
                {"id": item.item_id, "name": item.name, "okpd2": item.okpd2, "origin": "notice"}
                for item in lot.notice.positions
            ],
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
                    "matches": position_matches(upload, lot, candidate),
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
