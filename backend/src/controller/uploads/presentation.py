from urllib.parse import urlsplit

from src.models.upload import LotRecommendation, Upload


def safe_url(value: str) -> str:
    parsed = urlsplit(value)
    return value if parsed.scheme in {"https", "http"} and parsed.hostname else ""


def profile_summary(profile: str) -> str:
    text = " ".join(profile.split())
    return text if len(text) <= 650 else text[:650].rsplit(" ", 1)[0] + "…"


def lot_summary(lot: LotRecommendation) -> dict:
    return {
        "id": lot.notice.lot_id,
        "title": lot.notice.title,
        "subject": lot.notice.subject,
        "status": "needsCheck" if lot.candidates else "noCandidates",
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
        "counts": {"ready": 0, "needsCheck": found, "noCandidates": len(upload.lots) - found},
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
                    "role": f"Исторический профиль: {candidate.category}",
                    "status": "historical",
                    "summary": profile_summary(
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
                    "matches": [],
                    "similarPurchases": None,
                    "wins": None,
                    "purchases": [],
                    "clarify": [
                        "Уточните текущий ассортимент, наличие и условия поставки.",
                    ],
                }
                for candidate in lot.candidates
            ],
        },
    }
