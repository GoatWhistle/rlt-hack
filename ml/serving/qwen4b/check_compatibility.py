import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx
import numpy as np

MODEL = "Qwen/Qwen3-Embedding-4B"
SAMPLES = [
    "Instruct: Given a Russian procurement request, retrieve relevant supplier product offers.\nQuery: Питьевая вода в бутылках 19 литров",
    "Instruct: Given a Russian procurement request, retrieve relevant supplier product offers.\nQuery: Бумага офисная А4 80 г/м2 500 листов 17.12.14.110",
    "Instruct: Given a Russian procurement request, retrieve relevant supplier product offers.\nQuery: Перчатки защитные нитриловые размер L",
    "Instruct: Given a Russian procurement request, retrieve relevant supplier product offers.\nQuery: Манометры, насосы и запасные части для оборудования",
    "Instruct: Given a Russian procurement request, retrieve relevant supplier product offers.\nQuery: Крупа гречневая, крупа манная, кофе и картофельный крахмал",
    "Питьевая вода в бутылках 19 литров. Производство и доставка.",
    "Бумага офисная А4 80 г/м2 500 листов. Белизна 146%.",
    "Перчатки защитные нитриловые размер L. Без пудры.",
    "Насосы промышленные и манометры. Запасные части.",
    "Крупа гречневая, крупа манная. Пищевые продукты.",
]


async def encode(url: str, token: str) -> np.ndarray:
    async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
        response = await client.post(
            url.rstrip("/") + "/embeddings",
            headers={"Authorization": "Bearer " + token} if token else {},
            json={"model": MODEL, "input": SAMPLES, "encoding_format": "float"},
        )
        response.raise_for_status()
        rows = sorted(response.json()["data"], key=lambda row: row["index"])
        if [row["index"] for row in rows] != list(range(len(SAMPLES))):
            raise ValueError("Unexpected response ordering")
        vectors = np.asarray([row["embedding"] for row in rows], dtype=np.float64)
        if vectors.shape != (len(SAMPLES), 2560) or not np.isfinite(vectors).all():
            raise ValueError("Invalid embeddings")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if (norms == 0).any():
            raise ValueError("Empty embeddings")
        return vectors / norms


async def run(args):
    remote, local = await asyncio.gather(
        encode(os.environ["EMBEDDING_INFERENCE_URL"], os.getenv("EMBEDDING_INFERENCE_TOKEN", "")),
        encode(args.local_url, ""),
    )
    cosines = np.sum(remote * local, axis=1)
    difference = float(np.max(np.abs(remote - local)))
    passed = float(cosines.min()) >= args.min_cosine and difference <= args.max_difference
    report = {
        "samples": len(SAMPLES),
        "dimensions": 2560,
        "min_cosine": float(cosines.min()),
        "mean_cosine": float(cosines.mean()),
        "max_absolute_difference": difference,
        "thresholds": {"min_cosine": args.min_cosine, "max_difference": args.max_difference},
        "compatible": passed,
        "scope": "synthetic numerical compatibility; not ranking quality",
    }
    args.report.write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    if not passed:
        raise SystemExit("Compatibility check failed; keep current encoder")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-url", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--min-cosine", type=float, default=0.995)
    parser.add_argument("--max-difference", type=float, default=0.02)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
