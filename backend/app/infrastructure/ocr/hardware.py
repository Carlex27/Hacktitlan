"""Read-only hardware detection for optional local OCR packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import ctypes
import platform
import shutil
import subprocess
from typing import Callable


@dataclass(frozen=True)
class GpuDevice:
    vendor: str
    name: str
    memory_mb: int | None
    driver_version: str | None
    compute_capability: str | None


@dataclass(frozen=True)
class HardwareProfile:
    architecture: str
    operating_system: str
    total_memory_mb: int | None
    available_memory_mb: int | None
    gpus: tuple[GpuDevice, ...]
    compatibility: str
    reasons: tuple[str, ...]

    def as_dict(self) -> dict:
        return {**asdict(self), "gpus": [asdict(gpu) for gpu in self.gpus]}


def _windows_memory() -> tuple[int | None, int | None]:
    if platform.system() != "Windows":
        return None, None

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_physical", ctypes.c_ulonglong),
            ("available_physical", ctypes.c_ulonglong),
            ("total_page_file", ctypes.c_ulonglong),
            ("available_page_file", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("available_virtual", ctypes.c_ulonglong),
            ("available_extended_virtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None, None
    divisor = 1024 * 1024
    return status.total_physical // divisor, status.available_physical // divisor


def _nvidia_gpus(run: Callable[..., subprocess.CompletedProcess[str]]) -> tuple[GpuDevice, ...]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return ()
    try:
        result = run(
            [
                executable,
                "--query-gpu=name,memory.total,driver_version,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if result.returncode != 0:
        return ()
    devices: list[GpuDevice] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 4:
            continue
        try:
            memory_mb = int(parts[1])
        except ValueError:
            memory_mb = None
        devices.append(GpuDevice("NVIDIA", parts[0], memory_mb, parts[2] or None, parts[3] or None))
    return tuple(devices)


def probe_hardware(
    *,
    memory_probe: Callable[[], tuple[int | None, int | None]] = _windows_memory,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> HardwareProfile:
    architecture = platform.machine().lower()
    total_memory_mb, available_memory_mb = memory_probe()
    gpus = _nvidia_gpus(run)
    reasons: list[str] = []

    if architecture not in {"amd64", "x86_64"}:
        compatibility = "unsupported"
        reasons.append("OCR local requiere arquitectura x64")
    elif total_memory_mb is not None and total_memory_mb < 6 * 1024:
        compatibility = "unsupported"
        reasons.append("Menos de 6 GB de RAM")
    elif total_memory_mb is None:
        compatibility = "unknown"
        reasons.append("No se pudo medir la memoria")
    elif total_memory_mb < 8 * 1024:
        compatibility = "supported_with_limits"
        reasons.append("Menos de los 8 GB recomendados")
    else:
        compatibility = "supported"
        reasons.append("CPU x64 y memoria compatibles")
    if gpus:
        reasons.append("GPU NVIDIA detectada; aceleración sujeta a validación del runtime")
    else:
        reasons.append("Se utilizará CPU si no existe un runtime GPU compatible")

    return HardwareProfile(
        architecture=architecture,
        operating_system=platform.platform(),
        total_memory_mb=total_memory_mb,
        available_memory_mb=available_memory_mb,
        gpus=gpus,
        compatibility=compatibility,
        reasons=tuple(reasons),
    )
