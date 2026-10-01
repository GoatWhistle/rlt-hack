"""Разовая загрузка весов перед запуском моделей без внешних запросов."""

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

from rlt_ml.common import read_config, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", help="HF model id; можно повторять")
    parser.add_argument("--config", type=Path, default=Path("ml/configs/retrieval.toml"))
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    models = args.model or read_config(args.config)["models"]
    versions = {}
    for model_id in models:
        path = Path(snapshot_download(
            model_id,
            allow_patterns=["*.json", "*.safetensors", "tokenizer.model", "*.txt", "*.tiktoken"],
        ))
        versions[model_id] = {"revision": path.name, "snapshot_path": str(path)}
        print(f"Готов кеш {model_id}: {path.name}", flush=True)
    write_json(args.manifest, versions)


if __name__ == "__main__":
    main()
