import httpx

from src.adapter.client.errors import EmbeddingClientError

QUERY_INSTRUCTION = (
    "Given a Russian procurement request, retrieve relevant supplier product offers."
)


class OllamaEmbedder:
    def __init__(
        self,
        http: httpx.AsyncClient,
        model: str,
        dimensions: int = 2560,
        context_length: int = 512,
        expected_digest: str = "",
    ) -> None:
        self._http = http
        self._model = model
        self.dimensions = dimensions
        self._context_length = context_length
        self._expected_digest = expected_digest
        self._digest = ""
        self.model_key = ""

    async def initialize(self) -> None:
        self._digest = await self._model_digest()
        if self._expected_digest and self._digest != self._expected_digest:
            raise EmbeddingClientError("локальные веса не совпадают с ожидаемой ревизией")
        self.model_key = (
            f"ollama/{self._model}@{self._digest}/offer-v1-query-v1"
            f"/ctx{self._context_length}/dim{self.dimensions}"
        )

    async def _model_digest(self) -> str:
        try:
            response = await self._http.get("/api/tags")
            response.raise_for_status()
            for model in response.json()["models"]:
                if model["name"] == self._model:
                    return str(model["digest"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise EmbeddingClientError("не удалось проверить локальные веса") from error
        raise EmbeddingClientError("модель отсутствует в локальном кеше; сначала загрузите веса")

    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        if not self.model_key or await self._model_digest() != self._digest:
            raise EmbeddingClientError("ревизия модели изменилась; перезапустите воркер")
        inputs = (
            [f"Instruct: {QUERY_INSTRUCTION}\nQuery: {text}" for text in texts] if query else texts
        )
        try:
            response = await self._http.post(
                "/api/embed",
                json={
                    "model": self._model,
                    "input": inputs,
                    "dimensions": self.dimensions,
                    "truncate": True,
                    "keep_alive": "5m",
                    "options": {"num_ctx": self._context_length, "num_thread": 2},
                },
            )
            response.raise_for_status()
            return [[float(value) for value in row] for row in response.json()["embeddings"]]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise EmbeddingClientError("ошибка локального эмбеддера") from error
