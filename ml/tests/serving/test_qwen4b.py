import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

httpx = pytest.importorskip("httpx")
torch = pytest.importorskip("torch")
pytest.importorskip("fastapi")
pytest.importorskip("transformers")


@pytest.fixture
def module(monkeypatch, tmp_path):
    monkeypatch.setenv("QWEN4B_MODEL_DIR", str(tmp_path))
    path = Path(__file__).parents[2] / "serving" / "qwen4b" / "api.py"
    spec = importlib.util.spec_from_file_location("qwen4b_api", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class Tokens(dict):
    def to(self, device):
        return self


class Tokenizer:
    def __call__(self, texts, **kwargs):
        return Tokens(input_ids=torch.ones((len(texts), 3), dtype=torch.long))


class Model:
    def __call__(self, **tokens):
        return SimpleNamespace(last_hidden_state=torch.ones((len(tokens["input_ids"]), 3, 2560)))


def test_local_encoder_preserves_order_and_normalizes(module):
    encoder = module.Encoder.__new__(module.Encoder)
    encoder.tokenizer = Tokenizer()
    encoder.model = Model()
    result = encoder.encode(["one", "two"])
    assert len(result) == 2
    assert len(result[0]) == 2560
    assert sum(value * value for value in result[0]) == pytest.approx(1.0)


def test_local_encoder_rejects_long_input_instead_of_truncation(module, monkeypatch):
    monkeypatch.setattr(module, "MAX_TOKENS", 2)
    encoder = module.Encoder.__new__(module.Encoder)
    encoder.tokenizer = Tokenizer()
    encoder.model = Model()
    with pytest.raises(ValueError, match="no truncation"):
        encoder.encode(["three tokens"])


def test_endpoint_validates_model_and_request_order(module):
    async def run():
        module.app.state.encoder = SimpleNamespace(
            encode=lambda texts: [[float(i)] * 2560 for i, _ in enumerate(texts)]
        )
        module.app.state.lock = asyncio.Lock()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=module.app), base_url="http://test"
        ) as client:
            bad = await client.post("/embeddings", json={"model": "other", "input": ["one"]})
            assert bad.status_code == 400
            response = await client.post(
                "/embeddings", json={"model": module.MODEL, "input": ["one", "two"]}
            )
            assert response.status_code == 200
            assert [row["index"] for row in response.json()["data"]] == [0, 1]
            empty = await client.post("/embeddings", json={"model": module.MODEL, "input": [""]})
            assert empty.status_code == 400

    asyncio.run(run())
