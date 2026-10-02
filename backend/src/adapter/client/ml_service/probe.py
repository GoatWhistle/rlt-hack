import httpx

from src.adapter.client.errors import MlServiceUnavailableError

HEALTH_PATH = "/api/health"
PROBE_NAME = "semantic"


class MlServiceProbe:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return PROBE_NAME

    @property
    def required(self) -> bool:
        return False

    async def check(self) -> None:
        try:
            response = await self._client.get(HEALTH_PATH)
        except httpx.TransportError as error:
            raise MlServiceUnavailableError(type(error).__name__) from error
        if response.is_error:
            raise MlServiceUnavailableError(f"status {response.status_code}")
