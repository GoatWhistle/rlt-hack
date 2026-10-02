import httpx
import pytest

from src.controller.uploads.received import MAX_BYTES
from tests.controller.uploads.conftest import CSV, FakeEngine, assert_error

Files = dict[str, tuple[str, bytes, str]]


def csv_file(content: bytes, name: str = "notices.csv") -> Files:
    return {"file": (name, content, "text/csv")}


async def upload(client: httpx.AsyncClient, content: bytes = CSV) -> httpx.Response:
    return await client.post("/api/uploads", files=csv_file(content))


async def test_upload_keeps_the_summary_shape(search_client: httpx.AsyncClient) -> None:
    response = await upload(search_client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["fileName"] == "notices.csv"
    assert (body["total"], body["processed"], body["counts"]["ready"]) == (1, 1, 1)
    assert "rlt_session" in response.cookies
    lot = await search_client.get(f"/api/uploads/{body['id']}/lots/L1")
    assert lot.json()["recommendation"]["companies"][0]["inn"] == "1111111111"


@pytest.mark.parametrize(
    ("content", "status", "code"),
    [
        (b"PK\x03\x04xlsx", 415, "unsupported_file_type"),
        (b"lot_id;procedure_name" + b";" * 70_000 + b"\nL1;x\n", 422, "invalid_file"),
        (b"", 422, "invalid_file"),
        (b"title;subject\nx;y\n", 422, "missing_columns"),
        (b"lot_id;procedure_name\nL1;a\nL1;b\n", 422, "invalid_row"),
        (
            b"lot_id;procedure_name\n" + b"".join(b"L%d;x\n" % index for index in range(21)),
            422,
            "too_many_rows",
        ),
    ],
    ids=["binary", "wide", "empty", "columns", "row", "rows"],
)
async def test_rejected_files_answer_with_a_code(
    search_client: httpx.AsyncClient, engine: FakeEngine, content: bytes, status: int, code: str
) -> None:
    assert_error(await upload(search_client, content), status, code)
    assert engine.calls == 0


async def test_invalid_row_message_names_the_line(search_client: httpx.AsyncClient) -> None:
    body = assert_error(
        await upload(search_client, b"lot_id;procedure_name\nL1;a\nL1;b\n"), 422, "invalid_row"
    )
    assert body["message"].startswith("line 3:")


async def test_missing_file_field(search_client: httpx.AsyncClient) -> None:
    response = await search_client.post("/api/uploads", data={"other": "x"})
    assert_error(response, 400, "missing_file")


async def test_declared_oversized_body_is_refused_before_reading(
    search_client: httpx.AsyncClient,
) -> None:
    content = b"lot_id;procedure_name\n" + b"x" * (MAX_BYTES + 128 * 1024)
    assert_error(await upload(search_client, content), 413, "file_too_large")


async def test_file_just_over_the_limit_is_too_large(search_client: httpx.AsyncClient) -> None:
    content = b"lot_id;procedure_name\n" + b"x" * MAX_BYTES
    assert_error(await upload(search_client, content), 413, "file_too_large")


async def test_unknown_upload_and_lot(search_client: httpx.AsyncClient) -> None:
    assert_error(await search_client.get(f"/api/uploads/{'a' * 32}"), 404, "upload_not_found")
    created = (await upload(search_client)).json()["id"]
    response = await search_client.get(f"/api/uploads/{created}/lots/missing")
    assert_error(response, 404, "lot_not_found")
    evidence = f"/api/uploads/{created}/lots/L1/evidence/1111111111/none"
    assert_error(await search_client.get(evidence), 404, "not_found")
    assert_error(await search_client.get("/api/unknown"), 404, "not_found")


async def test_invalid_body_is_invalid_request(search_client: httpx.AsyncClient) -> None:
    created = (await upload(search_client)).json()["id"]
    response = await search_client.post(f"/api/uploads/{created}/results", json={"lotIds": []})
    assert_error(response, 422, "invalid_request")


async def test_search_failure_during_upload_is_unavailable(
    search_client: httpx.AsyncClient, engine: FakeEngine
) -> None:
    engine.failure = RuntimeError("encoder is down")
    response = await upload(search_client)
    assert_error(response, 503, "search_unavailable")
    assert response.headers["Retry-After"] == "5"


async def test_supplier_search_errors(search_client: httpx.AsyncClient, engine: FakeEngine) -> None:
    found = await search_client.post("/api/suppliers/search", json={"query": "paper"})
    assert found.json()["suppliers"][0]["inn"] == "1111111111"
    blank = await search_client.post("/api/suppliers/search", json={"query": "  "})
    assert_error(blank, 422, "empty_query")
    empty = await search_client.post("/api/suppliers/search", json={"query": ""})
    assert_error(empty, 422, "invalid_request")
    engine.failure = RuntimeError("encoder is down")
    failed = await search_client.post("/api/suppliers/search", json={"query": "paper"})
    assert_error(failed, 503, "search_unavailable")
