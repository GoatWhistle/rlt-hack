"""Контрастивное дообучение энкодера с исключением известных ложных отрицательных пар."""

import argparse
import math
import random
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as parquet
import torch

from rlt_ml.common import read_config, revision, write_json
from rlt_ml.text_encoder import TextEncoder


def contrastive_masks(rows: list[dict]):
    positives, valid = [], []
    for row in rows:
        positive = [row["query_text"] == other["query_text"] for other in rows]
        known = set(row["known_positive_inns"])
        allowed = [p or other["supplier_inn"] not in known
                   for p, other in zip(positive, rows, strict=True)]
        positives.append(positive)
        valid.append(allowed)
    return positives, valid


def contrastive_loss(query_vectors, card_vectors, rows: list[dict], temperature: float):
    positives, valid = contrastive_masks(rows)
    device = query_vectors.device
    positive = torch.tensor(positives, device=device)
    allowed = torch.tensor(valid, device=device)
    scores = (query_vectors.float() @ card_vectors.float().T) / temperature
    numerator = torch.logsumexp(scores.masked_fill(~positive, -torch.inf), dim=1)
    denominator = torch.logsumexp(scores.masked_fill(~allowed, -torch.inf), dim=1)
    useful = (allowed & ~positive).any(dim=1)
    weights = torch.tensor([r["sample_weight"] for r in rows], device=device) * useful
    loss = ((denominator - numerator) * weights).sum() / weights.sum().clamp_min(1e-8)
    return loss, bool(useful.any())


def train(data: Path, out: Path, config: dict) -> dict:
    if out.exists():
        raise FileExistsError(f"Выберите новый каталог запуска: {out}")
    if not torch.cuda.is_available():
        raise RuntimeError("GPU-обучение требует CUDA; CPU-проверка: rlt-gpu-check --allow-cpu")
    if config["batch_size"] < 2 or config["gradient_accumulation"] < 1:
        raise ValueError("batch_size >= 2 и gradient_accumulation >= 1")
    if config["precision"] != "bf16" or not torch.cuda.is_bf16_supported():
        raise ValueError("Эта конфигурация требует bf16 на CUDA GPU")
    if config["max_steps"] < 0 or config["epochs"] < 1 or config["save_every"] < 1:
        raise ValueError("Неверные ограничения длины обучения")
    seed = int(config["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    rows = parquet.read_table(data / "train/encoder_pairs.parquet").to_pylist()
    random.shuffle(rows)
    if config["max_train_pairs"]:
        rows = rows[:config["max_train_pairs"]]
    if len(rows) < 2:
        raise ValueError("Недостаточно положительных пар")
    encoder = TextEncoder(config["model"], config["max_length"], config.get("query_instruction", ""))
    if config.get("lora_rank"):
        from peft import LoraConfig, TaskType, get_peft_model

        encoder.model = get_peft_model(encoder.model, LoraConfig(
            task_type=TaskType.FEATURE_EXTRACTION, r=config["lora_rank"],
            lora_alpha=config["lora_alpha"], lora_dropout=config["lora_dropout"],
            target_modules=config["lora_target_modules"], bias="none",
        ))
    if config["gradient_checkpointing"]:
        encoder.model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False}
        )
    parameters = [p for p in encoder.model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(
        parameters, lr=config["learning_rate"], weight_decay=config["weight_decay"]
    )
    out.mkdir(parents=True)
    write_json(out / "config.json", config)
    encoder.model.train()
    optimizer.zero_grad(set_to_none=True)
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    steps, accumulated, skipped, losses = 0, 0, 0, []
    stop = False
    for _epoch in range(config["epochs"]):
        random.shuffle(rows)
        batches = math.ceil(len(rows) / config["batch_size"])
        for batch_index in range(batches):
            batch = rows[batch_index * config["batch_size"]:(batch_index + 1) * config["batch_size"]]
            with torch.autocast("cuda", dtype=torch.bfloat16):
                query_vectors = encoder([r["query_text"] for r in batch], query=True)
                card_vectors = encoder([r["profile_text"] for r in batch], query=False)
                loss, useful = contrastive_loss(query_vectors, card_vectors, batch, config["temperature"])
            if not torch.isfinite(loss):
                raise RuntimeError("Нечисловое значение loss; запуск остановлен")
            if useful:
                (loss / config["gradient_accumulation"]).backward()
                accumulated += 1
                losses.append(float(loss.detach()))
            else:
                skipped += 1
            if accumulated and (accumulated == config["gradient_accumulation"] or batch_index == batches - 1):
                if accumulated != config["gradient_accumulation"]:
                    for parameter in parameters:
                        if parameter.grad is not None:
                            parameter.grad.mul_(config["gradient_accumulation"] / accumulated)
                torch.nn.utils.clip_grad_norm_(parameters, 1.0)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                accumulated = 0
                steps += 1
                if steps % 10 == 0:
                    print(f"step={steps} loss={np.mean(losses[-80:]):.4f}", flush=True)
                if steps % config["save_every"] == 0:
                    encoder.save(out / f"checkpoint-{steps}", config)
                if config["max_steps"] and steps >= config["max_steps"]:
                    stop = True
                    break
        if stop:
            break
    if steps == 0:
        raise ValueError("Нет батчей с допустимыми отрицательными примерами")
    torch.cuda.synchronize()
    seconds = time.monotonic() - started
    encoder.save(out / "encoder", config)
    report = {
        "source_git_revision": revision(), "config": config,
        "base_model_revision": encoder.base_revision,
        "train_pairs": len(rows), "optimizer_steps": steps, "skipped_batches": skipped,
        "trainable_parameters": sum(p.numel() for p in parameters),
        "duration_seconds": round(seconds, 2), "seconds_per_step": round(seconds / steps, 3),
        "peak_vram_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
        "peak_vram_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2),
        "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(), "loss_mean": float(np.mean(losses)),
        "limitations": [
            "In-batch negatives — слабая разметка; известные положительные пары исключены из negatives.",
            "Накопление градиентов увеличивает эффективный batch, но не пул negatives.",
            "Loss не заменяет Recall@100 на общей выборке с новыми поставщиками.",
            "Сохранённые checkpoints предназначены для оценки; возобновление optimizer не реализовано.",
        ],
    }
    write_json(out / "report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("ml/configs/qwen_5060ti.toml"))
    parser.add_argument("--max-steps", type=int)
    args = parser.parse_args()
    config = read_config(args.config)
    if args.max_steps is not None:
        config["max_steps"] = args.max_steps
    print(train(args.data, args.out, config))


if __name__ == "__main__":
    main()
