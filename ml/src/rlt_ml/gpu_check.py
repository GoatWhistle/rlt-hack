"""Проверка CUDA, квоты CPU, bf16 и реального выполнения GPU-операций."""

import argparse
import json
import os
import shutil
from pathlib import Path

import torch


def inspect(allow_cpu: bool = False) -> dict:
    result = {
        "torch": torch.__version__, "torch_cuda": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "cpu_affinity": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count(),
        "disk_free_gib": round(shutil.disk_usage(Path.cwd()).free / 2**30, 1),
    }
    quota = Path("/sys/fs/cgroup/cpu.max")
    if quota.exists():
        values = quota.read_text().split()
        result["cpu_quota"] = float(values[0]) / float(values[1]) if values[0] != "max" else "unlimited"
    if not result["cuda_available"]:
        if allow_cpu:
            return result
        raise RuntimeError("CUDA недоступна. Проверьте драйвер, GPU в контейнере и CUDA-сборку torch")
    props = torch.cuda.get_device_properties(0)
    result.update({
        "gpu": props.name, "vram_gib": round(props.total_memory / 2**30, 2),
        "free_vram_gib": round(torch.cuda.mem_get_info()[0] / 2**30, 2),
        "compute_capability": list(torch.cuda.get_device_capability()),
        "bf16": torch.cuda.is_bf16_supported(), "compiled_arches": torch.cuda.get_arch_list(),
    })
    a = torch.randn(256, 256, device="cuda", dtype=torch.bfloat16, requires_grad=True)
    (a @ a.T).float().square().mean().backward()
    torch.cuda.synchronize()
    result["bf16_forward_backward"] = bool(torch.isfinite(a.grad).all())
    if not result["bf16_forward_backward"]:
        raise RuntimeError("GPU-тест вернул нечисловой градиент")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()
    print(json.dumps(inspect(args.allow_cpu), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
