from src.models.upload import LotRecommendation, Upload


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
                    "name": f"Поставщик ИНН {candidate.inn}",
                    "inn": candidate.inn,
                    "role": f"Исторический профиль: {candidate.category}",
                    "status": "check",
                    "checkReason": "Проверьте актуальный ассортимент и реквизиты компании.",
                    "summary": candidate.profile,
                    "matches": [],
                    "similarPurchases": None,
                    "wins": None,
                    "purchases": [],
                    "clarify": [
                        "Подтвердите соответствие запросу: найден профиль из истории закупок.",
                        "Контакты, наличие и статистика побед в этом поиске не проверялись.",
                    ],
                }
                for candidate in lot.candidates
            ],
        },
    }
