import json
from dataclasses import dataclass
from types import TracebackType
from typing import Self

import httpx


@dataclass(frozen=True, slots=True)
class ClickHouseAddress:
    url: str = "http://localhost:8123"
    user: str = "default"
    password: str = ""


class ClickHouseHttp:
    def __init__(self, address: ClickHouseAddress, timeout: float = 900.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=address.url,
            timeout=timeout,
            headers={"X-ClickHouse-User": address.user, "X-ClickHouse-Key": address.password},
        )

    async def execute(self, statement: str, settings: dict[str, str] | None = None) -> str:
        response = await self._client.post("/", content=statement.encode(), params=settings)
        if response.status_code != httpx.codes.OK:
            raise RuntimeError(response.text[:2000])
        return response.text

    async def rows(self, statement: str) -> list[dict[str, object]]:
        text = await self.execute(statement + " FORMAT JSONEachRow")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    async def scalar(self, statement: str) -> int:
        return int((await self.execute(statement)).strip() or 0)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.aclose()
