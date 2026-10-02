import json
from pathlib import Path

from src.adapter.repository.uploads.files import FileUploads
from src.models.operations.upload import LotRecommendation, Notice, Upload

OWNER = "a" * 32
UPLOAD = "b" * 32


async def test_upload_without_progress_fields_reads_as_processed(tmp_path: Path) -> None:
    folder = tmp_path / OWNER
    folder.mkdir()
    document = {
        "upload_id": UPLOAD,
        "owner": OWNER,
        "filename": "a.csv",
        "created_at": "2026-10-02",
        "lots": [{"notice": {"lot_id": "L1", "title": "paper"}, "candidates": []}],
        "ranking_version": "v1",
    }
    (folder / f"{UPLOAD}.json").write_text(json.dumps(document), encoding="utf-8")
    upload = await FileUploads(tmp_path).get(OWNER, UPLOAD)
    assert upload is not None
    assert upload.lots == [LotRecommendation(Notice("L1", "paper"))]
    assert upload.lots[0].processed
    assert not upload.lots[0].failed


async def test_progress_fields_survive_a_round_trip(tmp_path: Path) -> None:
    repository = FileUploads(tmp_path)
    upload = Upload(
        UPLOAD,
        OWNER,
        "a.csv",
        "2026-10-02",
        [
            LotRecommendation(Notice("L1", "paper"), processed=False),
            LotRecommendation(Notice("L2", "pens"), failed=True),
        ],
    )
    await repository.save(upload)
    assert await repository.get(OWNER, UPLOAD) == upload
