"""Воспроизводимые демонстрационные кейсы (E1).

Скрипт выполняет сценарии через HTTP API, сохраняет идентификаторы архивных
результатов и краткий снимок оснований. Сохранённый кейс открывается по
`/search/{searchId}` или `/uploads/{id}/lots/{lot}` и показывает дату
результата: его нельзя выдавать за только что выполненный поиск.

    uv run python scripts/demo_cases.py --api http://localhost:8080 --out ../docs/demo/cases.json
"""

import argparse
import http.cookiejar
import json
import time
import urllib.request
import uuid
from pathlib import Path

SEARCHES = (
    (
        "multi",
        "Несколько позиций с разным покрытием",
        "Бумага офисная А4 80 г/м2; кабель ВВГнг 3х2,5; перчатки трикотажные",
    ),
    ("requirements", "Проверка обязательных параметров по карточкам", "Бумага А4 100 г/м2"),
    (
        "insufficient",
        "Параметр не указан в карточках — данных недостаточно",
        "Светильник светодиодный 18 Вт",
    ),
)
TOP = 5


class Client:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def call(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        content_type: str = "application/json",
    ) -> dict:
        request = urllib.request.Request(
            self.base + path, data=body, method=method, headers={"Content-Type": content_type}
        )
        with self.opener.open(request, timeout=60) as response:
            return json.loads(response.read())


def snapshot(search: dict) -> dict:
    return {
        "searchId": search["searchId"],
        "createdAt": search["createdAt"],
        "pipeline": search["pipeline"],
        "items": [
            {"name": item["name"], "requirements": item["requirements"]} for item in search["items"]
        ],
        "top": [
            {
                "rank": candidate["rank"],
                "name": candidate["name"],
                "inn": candidate["inn"],
                "status": candidate["status"],
                "novelty": candidate["novelty"],
                "roleBasis": candidate["roleBasis"],
                "matches": [
                    {
                        "item": match["itemId"],
                        "offer": (match.get("offer") or {}).get("name"),
                        "url": (match.get("offer") or {}).get("url"),
                        "observedAt": (match.get("offer") or {}).get("observedAt"),
                        "checks": [
                            f"{check['text']}:{check['status']}" for check in match["checks"]
                        ],
                    }
                    for match in candidate["matches"]
                ],
            }
            for candidate in search["candidates"][:TOP]
        ],
    }


def upload(client: Client, path: Path) -> dict:
    boundary = uuid.uuid4().hex
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            "Content-Type: text/csv\r\n\r\n"
        ).encode()
        + path.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    created = client.call("POST", "/api/uploads", body, f"multipart/form-data; boundary={boundary}")
    for _ in range(300):
        summary = client.call("GET", f"/api/uploads/{created['id']}/summary")
        if summary["processed"] == summary["total"]:
            break
        time.sleep(1)
    detail = client.call("GET", f"/api/uploads/{created['id']}")
    lot = detail["lots"][0]["id"]
    first = client.call("GET", f"/api/uploads/{created['id']}/lots/{lot}")
    return {
        "uploadId": created["id"],
        "counts": summary["counts"],
        "lots": [
            {"id": item["id"], "status": item["status"], "searchId": item["searchId"]}
            for item in detail["lots"]
        ],
        "firstLot": snapshot(first["search"]) if first.get("search") else None,
        "note": "загрузка видна только создавшей её сессии; показывайте в том же браузере",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True)
    parser.add_argument("--csv", type=Path, default=Path("../test-supplier-search.csv"))
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    client = Client(arguments.api)
    health = client.call("GET", "/api/health/ready")
    cases = []
    for key, title, text in SEARCHES:
        search = client.call("POST", "/api/searches", json.dumps({"text": text}).encode())
        cases.append({"key": key, "title": title, "query": text, **snapshot(search)})
    cases.append(
        {"key": "csv", "title": "CSV, закупки и выгрузка", **upload(client, arguments.csv)}
    )
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(
        json.dumps(
            {"api": arguments.api, "degraded": health.get("degraded", []), "cases": cases},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
