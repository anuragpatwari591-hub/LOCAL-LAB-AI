"""Hardware detection used by prepare (model selection) and diagnose."""

from __future__ import annotations

import platform
from dataclasses import asdict, dataclass

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a core dependency but keep this resilient
    psutil = None  # type: ignore[assignment]


@dataclass
class HardwareInfo:
    os_name: str
    os_release: str
    arch: str
    cpu_name: str
    logical_cores: int
    physical_cores: int
    total_ram_gb: float
    available_ram_gb: float
    gpu_detected: bool
    gpu_name: str | None

    def as_dict(self) -> dict:
        return asdict(self)


def _detect_gpu() -> tuple[bool, str | None]:
    """Best-effort GPU detection without requiring vendor SDKs.

    Only used to decide whether to advertise GPU offload as an option;
    the shipped default configuration always assumes CPU-only inference
    unless a user explicitly opts in.
    """
    try:
        import subprocess

        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, result.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return False, None


def detect_hardware() -> HardwareInfo:
    logical = 1
    physical = 1
    total_ram_gb = 0.0
    available_ram_gb = 0.0

    if psutil is not None:
        logical = psutil.cpu_count(logical=True) or 1
        physical = psutil.cpu_count(logical=False) or logical
        vm = psutil.virtual_memory()
        total_ram_gb = round(vm.total / (1024**3), 2)
        available_ram_gb = round(vm.available / (1024**3), 2)

    gpu_detected, gpu_name = _detect_gpu()

    return HardwareInfo(
        os_name=platform.system(),
        os_release=platform.release(),
        arch=platform.machine(),
        cpu_name=platform.processor() or "unknown",
        logical_cores=logical,
        physical_cores=physical,
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        gpu_detected=gpu_detected,
        gpu_name=gpu_name,
    )


def recommend_llm_profile(hw: HardwareInfo) -> dict:
    """Conservative model/thread/context recommendation.

    Never recommends a 7B+ model as the default; low-end hardware always
    gets the small Q4_K_M model with tight context/thread/batch limits.
    """
    threads = max(1, min(hw.physical_cores or hw.logical_cores, hw.logical_cores))

    if hw.total_ram_gb and hw.total_ram_gb < 6:
        return {
            "model_file": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "context_size": 2048,
            "threads": max(1, threads - 1) or 1,
            "batch_size": 256,
            "kv_cache_type": "q8_0",
            "tier": "low-end (<6GB RAM) - conservative defaults",
        }
    if hw.total_ram_gb and hw.total_ram_gb < 12:
        return {
            "model_file": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "context_size": 4096,
            "threads": threads,
            "batch_size": 512,
            "kv_cache_type": "q8_0",
            "tier": "mid-range (6-12GB RAM)",
        }
    return {
        "model_file": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "context_size": 8192,
        "threads": threads,
        "batch_size": 1024,
        "kv_cache_type": "f16",
        "tier": "high-end (>=12GB RAM) - larger model may be selected manually",
    }
