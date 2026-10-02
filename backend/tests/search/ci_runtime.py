import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Input(BaseModel):
    input: list[str]


@app.post("/embeddings")
async def embeddings(body: Input):
    return {
        "data": [{"index": i, "embedding": [1.0] + [0.0] * 2559} for i in range(len(body.input))]
    }


def prepare(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "card_id": "synthetic-paper",
                    "supplier_inn": "7801234564",
                    "category": "17.12",
                    "profile_text": "Бумага офисная А4 для принтера",
                }
            ]
        ),
        directory / "cards.parquet",
    )
    np.save(directory / "card_vectors.npy", np.array([[1.0] + [0.0] * 2559], dtype=np.float32))
    (directory / "report.json").write_text(json.dumps({"scope": "synthetic HTTP integration only"}))
    manifest = {
        "model": "Qwen/Qwen3-Embedding-4B",
        "revision": "synthetic-ci",
        "shape": [1, 2560],
        "query_instruction": "retrieve",
        "files": {
            name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("cards.parquet", "card_vectors.npy", "report.json")
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))


if __name__ == "__main__":
    if sys.argv[1] == "serve":
        uvicorn.run(app, host="0.0.0.0", port=8080)
    else:
        prepare(Path(sys.argv[1]))
