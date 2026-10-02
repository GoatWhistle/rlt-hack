from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from src.models.supplier_search import SupplierCandidate, SupplierCatalogOffer, SupplierPurchase
from src.models.upload import LotRecommendation, Notice, Upload


class FileUploads:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _folder(self, owner: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", owner):
            raise ValueError("invalid owner")
        return self.directory / owner

    async def save(self, upload: Upload) -> None:
        await asyncio.to_thread(self._save, upload)

    def _save(self, upload: Upload) -> None:
        folder = self._folder(upload.owner)
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = folder / f"{upload.upload_id}.tmp"
        document = asdict(upload)
        for lot in document["lots"]:
            price = lot["notice"].get("start_price")
            lot["notice"]["start_price"] = str(price) if price is not None else None
        temporary.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(folder / f"{upload.upload_id}.json")

    def _read(self, file: Path) -> Upload:
        data = json.loads(file.read_text(encoding="utf-8"))
        data["lots"] = [
            LotRecommendation(
                Notice(
                    **{
                        **lot["notice"],
                        "start_price": Decimal(str(lot["notice"]["start_price"]))
                        if lot["notice"].get("start_price") is not None
                        else None,
                    }
                ),
                [
                    SupplierCandidate(
                        **{
                            **candidate,
                            "purchases": [
                                SupplierPurchase(**item) for item in candidate.get("purchases", [])
                            ],
                            "catalog": [
                                SupplierCatalogOffer(**item)
                                for item in candidate.get("catalog", [])
                            ],
                        }
                    )
                    for candidate in lot["candidates"]
                ],
            )
            for lot in data["lots"]
        ]
        return Upload(**data)

    async def get(self, owner: str, upload_id: str) -> Upload | None:
        if not re.fullmatch(r"[a-f0-9]{32}", upload_id):
            return None
        return await asyncio.to_thread(self._get, owner, upload_id)

    def _get(self, owner: str, upload_id: str) -> Upload | None:
        file = self._folder(owner) / f"{upload_id}.json"
        return self._read(file) if file.exists() else None

    async def list(self, owner: str) -> list[Upload]:
        return await asyncio.to_thread(self._list, owner)

    def _list(self, owner: str) -> list[Upload]:
        paths = sorted(self._folder(owner).glob("*.json"), key=lambda file: file.stat().st_mtime)
        return [self._read(file) for file in reversed(paths[-100:])]
