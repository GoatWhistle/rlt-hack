import asyncio
import hashlib
import json
import math
import os
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, FiniteFloat
from transformers import AutoModel, AutoTokenizer

MODEL = "Qwen/Qwen3-Embedding-4B"
DIRECTORY = Path(os.environ["QWEN4B_MODEL_DIR"])
MAX_TOKENS = int(os.getenv("QWEN4B_MAX_TOKENS", "4096"))
BATCH_SIZE = int(os.getenv("QWEN4B_BATCH_SIZE", "8"))


class EmbeddingRequest(BaseModel):
    model: str
    input: list[str] = Field(min_length=1, max_length=64)
    encoding_format: str = "float"


class ProfileRequest(BaseModel):
    index_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    vector: list[FiniteFloat] = Field(min_length=2560, max_length=2560)


class ProfileScores:
    def __init__(self, directory: Path, *, device: str = "cuda") -> None:
        manifest = json.loads((directory / "manifest.json").read_text())
        if manifest.get("model") != MODEL:
            raise ValueError("Profile index must use Qwen3-Embedding-4B")
        path = directory / "card_vectors.npy"
        self.index_id = manifest["files"]["card_vectors.npy"]
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != self.index_id:
                raise ValueError("Profile vector checksum mismatch")
        vectors = np.load(path, allow_pickle=False)
        if (
            vectors.ndim != 2
            or vectors.shape[1] != 2560
            or vectors.shape[0] < 1
            or list(vectors.shape) != manifest["shape"]
            or not np.isfinite(vectors).all()
        ):
            raise ValueError("Invalid profile vector shape or values")
        self.matrix = torch.tensor(vectors, dtype=torch.float32, device=device)
        norms = torch.linalg.vector_norm(self.matrix, dim=1, keepdim=True)
        if not torch.isfinite(norms).all() or (norms <= 0).any():
            raise ValueError("Empty or invalid profile vectors")
        self.matrix.div_(norms)

    def score(self, index_id: str, vector: list[float]) -> list[float]:
        if index_id != self.index_id:
            raise ValueError("Profile index version mismatch")
        if len(vector) != 2560 or not all(math.isfinite(value) for value in vector):
            raise ValueError("Invalid query vector")
        query = torch.tensor(vector, dtype=torch.float32, device=self.matrix.device)
        norm = torch.linalg.vector_norm(query)
        if not torch.isfinite(norm) or norm <= 0:
            raise ValueError("Empty or invalid query vector")
        with torch.inference_mode():
            scores = self.matrix @ (query / norm)
            if not torch.isfinite(scores).all():
                raise ValueError("Non-finite profile scores")
            return scores.cpu().tolist()


class Encoder:
    def __init__(self) -> None:
        if not torch.cuda.is_available():
            raise RuntimeError("Qwen4B requires a working CUDA GPU")
        self.tokenizer = AutoTokenizer.from_pretrained(
            DIRECTORY, padding_side="left", local_files_only=True
        )
        self.model = (
            AutoModel.from_pretrained(
                DIRECTORY,
                local_files_only=True,
                torch_dtype=torch.float16,
                attn_implementation="sdpa",
            )
            .to("cuda")
            .eval()
        )
        self.model.config.use_cache = False
        if self.model.config.hidden_size != 2560:
            raise RuntimeError("Expected Qwen4B embeddings with 2560 dimensions")

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        with torch.inference_mode():
            for start in range(0, len(texts), BATCH_SIZE):
                batch = texts[start : start + BATCH_SIZE]
                tokens = self.tokenizer(batch, padding=True, return_tensors="pt")
                if tokens["input_ids"].shape[1] > MAX_TOKENS:
                    raise ValueError("Input exceeds token limit; no truncation was applied")
                tokens = tokens.to("cuda")
                hidden = self.model(**tokens).last_hidden_state[:, -1]
                result = functional.normalize(hidden.float(), p=2, dim=1)
                if not torch.isfinite(result).all():
                    raise RuntimeError("Non-finite embeddings")
                vectors.extend(result.cpu().tolist())
        return vectors


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.encoder = await asyncio.to_thread(Encoder)
    app.state.lock = asyncio.Lock()
    directory = os.getenv("QWEN4B_PROFILE_INDEX_DIR", "")
    app.state.profile_scores = (
        await asyncio.to_thread(ProfileScores, Path(directory)) if directory else None
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/profile-scores")
async def profile_scores(request: ProfileRequest):
    cache = getattr(app.state, "profile_scores", None)
    if cache is None:
        raise HTTPException(503, "Profile score cache is not configured")
    try:
        async with app.state.lock:
            scores = await asyncio.to_thread(cache.score, request.index_id, request.vector)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    except torch.cuda.OutOfMemoryError as error:
        raise HTTPException(503, "GPU memory exhausted") from error
    return {"index_id": cache.index_id, "scores": scores}


@app.get("/health")
async def health():
    return {"model": MODEL, "dimensions": 2560, "device": torch.cuda.get_device_name(0)}


@app.post("/embeddings")
async def embeddings(request: EmbeddingRequest):
    if request.model.casefold() != MODEL.casefold() or request.encoding_format != "float":
        raise HTTPException(400, "Only Qwen3-Embedding-4B float embeddings are supported")
    if any(not text.strip() or len(text) > 24000 for text in request.input):
        raise HTTPException(400, "Empty input or excessive input length")
    try:
        async with app.state.lock:
            vectors = await asyncio.to_thread(app.state.encoder.encode, request.input)
    except ValueError as error:
        raise HTTPException(413, str(error)) from error
    except torch.cuda.OutOfMemoryError as error:
        raise HTTPException(503, "GPU memory exhausted; reduce batch size") from error
    return {
        "object": "list",
        "model": MODEL,
        "data": [
            {"object": "embedding", "index": index, "embedding": vector}
            for index, vector in enumerate(vectors)
        ],
    }
