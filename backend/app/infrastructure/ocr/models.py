"""Managed lifecycle, validation, download, and storage of OCR models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import logging
from pathlib import Path
import shutil
from typing import Any, Callable
import urllib.request

from backend.app.infrastructure.ocr.manifest import (
    ModelFile,
    ModelPackageManifest,
    get_manifest,
)

logger = logging.getLogger(__name__)


class ModelManagementError(RuntimeError):
    """Raised when model installation, verification, or cleanup fails."""


class InsufficientDiskSpaceError(ModelManagementError):
    """Raised when available disk space is insufficient for model download."""


@dataclass(frozen=True)
class ModelPackageStatus:
    name: str
    version: str
    status: str  # "installed", "not_installed", "downloading", "corrupted"
    installed_files: int
    total_files: int
    installed_bytes: int
    total_bytes: int
    backend: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _default_downloader(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as response, destination.open("wb") as out_file:
        shutil.copyfileobj(response, out_file)


class OcrModelManager:
    """Manages local storage, verification, and downloads of OCR models outside the repo."""

    def __init__(
        self,
        model_root: str | Path,
        manifest: ModelPackageManifest | None = None,
        downloader: Callable[[str, Path], None] | None = None,
    ) -> None:
        self.model_root = Path(model_root)
        self.manifest = manifest or get_manifest()
        self.downloader = downloader or _default_downloader
        self.package_dir = self.model_root / self.manifest.name / self.manifest.version

    def check_disk_space(self, extra_safety_margin_bytes: int = 50 * 1024 * 1024) -> tuple[bool, int, int]:
        target_dir = self.model_root
        target_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(target_dir)
        free_bytes = getattr(usage, "free", usage[2] if len(usage) > 2 else 0)
        required = self.manifest.total_size_bytes + extra_safety_margin_bytes
        return free_bytes >= required, free_bytes, required

    def get_status(self) -> ModelPackageStatus:
        if not self.package_dir.is_dir():
            return ModelPackageStatus(
                name=self.manifest.name,
                version=self.manifest.version,
                status="not_installed",
                installed_files=0,
                total_files=len(self.manifest.files),
                installed_bytes=0,
                total_bytes=self.manifest.total_size_bytes,
                backend=self.manifest.backend,
                message="Paquete de modelos no descargado",
            )

        in_progress = any(self.package_dir.glob("**/*.part"))
        if in_progress:
            return ModelPackageStatus(
                name=self.manifest.name,
                version=self.manifest.version,
                status="downloading",
                installed_files=0,
                total_files=len(self.manifest.files),
                installed_bytes=0,
                total_bytes=self.manifest.total_size_bytes,
                backend=self.manifest.backend,
                message="Descarga de modelos en proceso",
            )

        installed_files = 0
        installed_bytes = 0
        corrupted_reasons: list[str] = []

        for item in self.manifest.files:
            file_path = self.package_dir / item.relative_path
            if not file_path.is_file():
                corrupted_reasons.append(f"Falta archivo {item.relative_path}")
                continue
            actual_size = file_path.stat().st_size
            if actual_size != item.size_bytes:
                corrupted_reasons.append(
                    f"Tamaño discordante en {item.relative_path}: {actual_size} != {item.size_bytes}"
                )
                continue
            actual_hash = _compute_sha256(file_path)
            if actual_hash != item.sha256:
                corrupted_reasons.append(f"Hash inválido en {item.relative_path}")
                continue
            installed_files += 1
            installed_bytes += actual_size

        if installed_files == len(self.manifest.files) and not corrupted_reasons:
            return ModelPackageStatus(
                name=self.manifest.name,
                version=self.manifest.version,
                status="installed",
                installed_files=installed_files,
                total_files=len(self.manifest.files),
                installed_bytes=installed_bytes,
                total_bytes=self.manifest.total_size_bytes,
                backend=self.manifest.backend,
                message="Paquete de modelos verificado e instalado",
            )

        return ModelPackageStatus(
            name=self.manifest.name,
            version=self.manifest.version,
            status="corrupted",
            installed_files=installed_files,
            total_files=len(self.manifest.files),
            installed_bytes=installed_bytes,
            total_bytes=self.manifest.total_size_bytes,
            backend=self.manifest.backend,
            message="; ".join(corrupted_reasons[:3]) or "Paquete de modelos incompleto o corrupto",
        )

    def verify(self) -> tuple[bool, list[str]]:
        status = self.get_status()
        if status.status == "installed":
            return True, []
        errors = [status.message] if status.message else ["El paquete no está completamente instalado"]
        return False, errors

    def download_file(self, file_spec: ModelFile) -> Path:
        target_path = self.package_dir / file_spec.relative_path
        if target_path.is_file() and target_path.stat().st_size == file_spec.size_bytes:
            if _compute_sha256(target_path) == file_spec.sha256:
                return target_path

        target_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = target_path.with_name(f"{target_path.name}.part")

        try:
            self.downloader(file_spec.download_url, part_path)
            if not part_path.is_file():
                raise ModelManagementError(f"Falló la descarga de {file_spec.name}")
            actual_hash = _compute_sha256(part_path)
            if actual_hash != file_spec.sha256:
                part_path.unlink(missing_ok=True)
                raise ModelManagementError(
                    f"Hash SHA-256 no coincide para {file_spec.name}: esperado {file_spec.sha256}, obtenido {actual_hash}"
                )
            part_path.replace(target_path)
            return target_path
        except Exception:
            part_path.unlink(missing_ok=True)
            raise

    def download_package(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> ModelPackageStatus:
        has_space, free_bytes, required_bytes = self.check_disk_space()
        if not has_space:
            raise InsufficientDiskSpaceError(
                f"Espacio insuficiente en disco: disponible {free_bytes // (1024*1024)} MB, requerido {required_bytes // (1024*1024)} MB"
            )

        self.package_dir.mkdir(parents=True, exist_ok=True)
        total_files = len(self.manifest.files)

        for index, file_spec in enumerate(self.manifest.files, 1):
            self.download_file(file_spec)
            if progress_callback:
                progress_callback(index, total_files)

        return self.get_status()

    def repair_package(self) -> ModelPackageStatus:
        has_space, free_bytes, required_bytes = self.check_disk_space()
        if not has_space:
            raise InsufficientDiskSpaceError("Espacio insuficiente en disco para reparación de modelos")

        self.package_dir.mkdir(parents=True, exist_ok=True)
        for file_spec in self.manifest.files:
            target_path = self.package_dir / file_spec.relative_path
            needs_redownload = (
                not target_path.is_file()
                or target_path.stat().st_size != file_spec.size_bytes
                or _compute_sha256(target_path) != file_spec.sha256
            )
            if needs_redownload:
                self.download_file(file_spec)

        return self.get_status()

    def remove_package(self) -> bool:
        if self.package_dir.exists():
            shutil.rmtree(self.package_dir, ignore_errors=True)
            parent = self.package_dir.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
            return True
        return False
