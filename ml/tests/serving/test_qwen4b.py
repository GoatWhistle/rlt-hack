import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

httpx = pytest.importorskip("httpx")
torch = pytest.importorskip("torch")
np = pytest.importorskip("numpy")
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


def index_directory(module, directory, *, zero=False):
    vectors = np.zeros((3, 2560), dtype=np.float32)
    vectors[0, 0] = 2
    vectors[1, 0] = -3
    vectors[2, 1] = 4 if not zero else 0
    np.save(directory / "card_vectors.npy", vectors, allow_pickle=False)
    digest = hashlib.sha256((directory / "card_vectors.npy").read_bytes()).hexdigest()
    manifest = {"model": module.MODEL, "shape": [3, 2560], "files": {"card_vectors.npy": digest}}
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return digest, manifest


def test_profile_cache_cpu_matches_normalized_cosine(module, tmp_path):
    digest, _ = index_directory(module, tmp_path)
    cache = module.ProfileScores(tmp_path, device="cpu")
    assert cache.matrix.dtype == torch.float32
    assert cache.score(digest, [5.0] + [0.0] * 2559) == pytest.approx([1.0, -1.0, 0.0])
    assert cache.score(digest, [0.0, 5.0] + [0.0] * 2558) == pytest.approx([0.0, 0.0, 1.0])
    with pytest.raises(ValueError, match="version mismatch"):
        cache.score("0" * 64, [1.0] * 2560)
    for vector in ([0.0] * 2560, [1.0], [float("nan")] * 2560):
        with pytest.raises(ValueError):
            cache.score(digest, vector)


@pytest.mark.parametrize("invalid", ["checksum", "shape", "model", "empty"])
def test_profile_cache_rejects_invalid_or_incompatible_snapshot(module, tmp_path, invalid):
    _, manifest = index_directory(module, tmp_path, zero=invalid == "empty")
    if invalid == "checksum":
        manifest["files"]["card_vectors.npy"] = "0" * 64
    elif invalid == "shape":
        manifest["shape"] = [2, 2560]
    elif invalid == "model":
        manifest["model"] = "Qwen/Qwen3-Embedding-0.6B"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        module.ProfileScores(tmp_path, device="cpu")


def test_profile_endpoint_checks_configuration_version_and_shape(module, tmp_path):
    digest, _ = index_directory(module, tmp_path)

    async def run():
        module.app.state.lock = asyncio.Lock()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=module.app), base_url="http://test"
        ) as client:
            payload = {"index_id": digest, "vector": [1.0] + [0.0] * 2559}
            unavailable = await client.post("/profile-scores", json=payload)
            assert unavailable.status_code == 503
            module.app.state.profile_scores = module.ProfileScores(tmp_path, device="cpu")
            good = await client.post("/profile-scores", json=payload)
            assert good.status_code == 200
            assert good.json() == {"index_id": digest, "scores": [1.0, -1.0, 0.0]}
            bad = await client.post("/profile-scores", json={**payload, "index_id": "0" * 64})
            assert bad.status_code == 409
            malformed = await client.post("/profile-scores", json={**payload, "vector": [1.0]})
            assert malformed.status_code == 422

    asyncio.run(run())
