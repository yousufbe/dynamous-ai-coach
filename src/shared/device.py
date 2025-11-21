from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DeviceInfo:
    """Summary of the selected device."""

    id: str
    name: str
    total_memory_gb: float | None
    source: str


def select_device(preferred_device: str) -> DeviceInfo:
    """Resolve and log the device that will be used for GPU workloads.

    Falls back to CPU when CUDA is not available or torch is missing.

    Args:
        preferred_device: Device string from configuration (e.g., ``"cuda:0"`` or ``"cpu"``).

    Returns:
        DeviceInfo describing the resolved device.
    """
    try:
        import torch  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        logger.info(
            "device_selected",
            device="cpu",
            reason="torch_not_available",
        )
        return DeviceInfo(id="cpu", name="cpu", total_memory_gb=None, source="cpu-fallback")

    if torch.cuda.is_available():  # type: ignore[attr-defined]
        _log_unsupported_gpus(torch)

    if preferred_device.startswith("cuda") and torch.cuda.is_available():  # type: ignore[attr-defined]
        try:
            device_index = torch.cuda.current_device() if preferred_device == "cuda" else int(preferred_device.split(":")[1])  # type: ignore[attr-defined]
            name = torch.cuda.get_device_name(device_index)  # type: ignore[attr-defined]
            total_mem = torch.cuda.get_device_properties(device_index).total_memory / (1024**3)  # type: ignore[attr-defined]
            logger.info(
                "device_selected",
                device=f"cuda:{device_index}",
                name=name,
                total_memory_gb=round(total_mem, 2),
                reason="config",
            )
            return DeviceInfo(
                id=f"cuda:{device_index}",
                name=name,
                total_memory_gb=round(total_mem, 2),
                source="cuda",
            )
        except Exception:  # pragma: no cover - defensive
            logger.warning("device_selection_failed", preferred=preferred_device)

    if torch.cuda.is_available():  # type: ignore[attr-defined]
        try:
            device_index = torch.cuda.current_device()  # type: ignore[attr-defined]
            name = torch.cuda.get_device_name(device_index)  # type: ignore[attr-defined]
            total_mem = torch.cuda.get_device_properties(device_index).total_memory / (1024**3)  # type: ignore[attr-defined]
            logger.info(
                "device_selected",
                device=f"cuda:{device_index}",
                name=name,
                total_memory_gb=round(total_mem, 2),
                reason="implicit",
            )
            return DeviceInfo(
                id=f"cuda:{device_index}",
                name=name,
                total_memory_gb=round(total_mem, 2),
                source="cuda-implicit",
            )
        except Exception:  # pragma: no cover - defensive
            logger.warning("device_selection_failed_fallback")

    logger.info(
        "device_selected",
        device="cpu",
        reason="cuda_unavailable",
    )
    return DeviceInfo(id="cpu", name="cpu", total_memory_gb=None, source="cpu-fallback")


def _log_unsupported_gpus(torch_module: Any) -> None:
    """Log GPUs that are present but below the supported CUDA capability."""

    try:
        device_count = torch_module.cuda.device_count()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - defensive
        return

    unsupported: list[dict[str, str]] = []
    for index in range(device_count):
        try:
            major, minor = torch_module.cuda.get_device_capability(index)  # type: ignore[attr-defined]
            if major < 7:
                name = torch_module.cuda.get_device_name(index)  # type: ignore[attr-defined]
                unsupported.append(
                    {"index": str(index), "name": name, "capability": f"{major}.{minor}"},
                )
        except Exception:  # pragma: no cover - defensive
            continue

    if unsupported:
        logger.warning(
            "device_unsupported_gpu_detected",
            gpus=unsupported,
            guidance="export CUDA_VISIBLE_DEVICES=0 to pin to supported GPU",
        )
