import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import torch
import torch.nn.functional as functional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoTokenizer

MODEL = "Qwen/Qwen3-Embedding-4B"
DIRECTORY = Path(os.environ["QWEN4B_MODEL_DIR"])
MAX_TOKENS = int(os.getenv("QWEN4B_MAX_TOKENS", "4096"))
BATCH_SIZE = int(os.getenv("QWEN4B_BATCH_SIZE", "8"))


class EmbeddingRequest(BaseModel):
    model: str
    input: list[str] = Field(min_length=1, max_length=64)
    encoding_format: str = "float"


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
    yield


app = FastAPI(lifespan=lifespan)


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
