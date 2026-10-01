"""Единый интерфейс к готовым Qwen, E5 и плотному энкодеру BGE-M3."""

import json
from pathlib import Path

import torch
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer


def family(model_id: str) -> str:
    name = model_id.lower()
    if "qwen3-embedding" in name:
        return "qwen"
    if "e5" in name:
        return "e5"
    if "bge-m3" in name:
        return "bge"
    raise ValueError(f"Неизвестный способ pooling/prompt: {model_id}")


def format_text(text: str, kind: str, query: bool, instruction: str) -> str:
    if kind == "qwen" and query:
        return f"Instruct: {instruction}\nQuery: {text}"
    if kind == "e5":
        return ("query: " if query else "passage: ") + text
    return text


def pool(hidden, mask, kind: str):
    if kind == "qwen":
        # Индекс последнего непустого токена подходит для левого и правого padding.
        indices = (mask * torch.arange(mask.shape[1], device=mask.device)).max(dim=1).values
        value = hidden[torch.arange(len(hidden), device=hidden.device), indices]
    elif kind == "e5":
        value = (hidden * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp_min(1)
    else:
        value = hidden[:, 0]
    return functional.normalize(value.float(), p=2, dim=1)


class TextEncoder:
    def __init__(self, model_id: str, max_length: int, instruction: str, device: str = "cuda",
                 offline: bool = True):
        model_path = Path(model_id)
        adapter = model_path.is_dir() and (model_path / "adapter_config.json").exists()
        metadata = {}
        if model_path.is_dir() and (model_path / "encoder_config.json").exists():
            metadata = json.loads((model_path / "encoder_config.json").read_text())
            base_id = metadata["model"]
        else:
            base_id = model_id
        self.kind = family(base_id)
        self.model_id = base_id
        self.device = device
        self.max_length = max_length
        self.instruction = metadata.get("query_instruction", instruction)
        dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
        source = base_id if adapter else model_id
        options = {"local_files_only": offline}
        if adapter and metadata.get("base_revision"):
            options["revision"] = metadata["base_revision"]
        self.tokenizer = AutoTokenizer.from_pretrained(
            source, padding_side="left" if self.kind == "qwen" else "right", **options
        )
        self.model = AutoModel.from_pretrained(
            source, torch_dtype=dtype, attn_implementation="sdpa", **options
        )
        self.base_revision = metadata.get("base_revision") or getattr(self.model.config, "_commit_hash", None)
        if adapter:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, str(model_path))
        if hasattr(self.model.config, "use_cache"):
            self.model.config.use_cache = False
        self.model.to(device)

    def __call__(self, texts: list[str], query: bool):
        texts = [format_text(t, self.kind, query, self.instruction) for t in texts]
        tokens = self.tokenizer(
            texts, padding=True, truncation=True, max_length=self.max_length, return_tensors="pt"
        ).to(self.device)
        hidden = self.model(**tokens).last_hidden_state
        return pool(hidden, tokens["attention_mask"], self.kind)

    def save(self, folder: Path, config: dict) -> None:
        from rlt_ml.common import write_json

        folder.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(folder, safe_serialization=True)
        self.tokenizer.save_pretrained(folder)
        write_json(folder / "encoder_config.json", {**config, "base_revision": self.base_revision})
