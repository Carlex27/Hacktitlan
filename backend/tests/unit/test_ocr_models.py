from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from backend.app.infrastructure.ocr.manifest import (
    ModelFile,
    ModelPackageManifest,
    get_manifest,
)
from backend.app.infrastructure.ocr.models import (
    InsufficientDiskSpaceError,
    ModelManagementError,
    OcrModelManager,
)


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_manifest_properties():
    manifest = get_manifest(backend="cpu")
    assert manifest.name == "PP-StructureV3"
    assert manifest.version == "3.0.0"
    assert manifest.license == "Apache-2.0"
    assert manifest.backend == "cpu"
    assert manifest.total_size_bytes > 0
    assert len(manifest.files) >= 5


def test_model_manager_status_when_not_installed(tmp_path: Path):
    manager = OcrModelManager(tmp_path)
    status = manager.get_status()
    assert status.status == "not_installed"
    assert status.installed_files == 0
    assert status.total_files > 0


def test_model_manager_status_when_downloading(tmp_path: Path):
    manager = OcrModelManager(tmp_path)
    pkg_dir = manager.package_dir
    pkg_dir.mkdir(parents=True)
    part_file = pkg_dir / "layout" / "inference.pdmodel.part"
    part_file.parent.mkdir(parents=True)
    part_file.write_bytes(b"partial")

    status = manager.get_status()
    assert status.status == "downloading"


def test_model_manager_download_and_verify(tmp_path: Path):
    content_a = b"fake-model-weights-a"
    content_b = b"fake-model-params-b"
    hash_a = _content_hash(content_a)
    hash_b = _content_hash(content_b)

    mini_manifest = ModelPackageManifest(
        name="test-ocr",
        version="1.0.0",
        license="Apache-2.0",
        description="Test models",
        language="en",
        backend="cpu",
        files=(
            ModelFile("model_a", "net/model.bin", hash_a, len(content_a), "https://example.com/a"),
            ModelFile("model_b", "net/params.bin", hash_b, len(content_b), "https://example.com/b"),
        ),
    )

    url_map = {
        "https://example.com/a": content_a,
        "https://example.com/b": content_b,
    }

    def fake_downloader(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(url_map[url])

    manager = OcrModelManager(tmp_path, manifest=mini_manifest, downloader=fake_downloader)
    status_before = manager.get_status()
    assert status_before.status == "not_installed"

    download_status = manager.download_package()
    assert download_status.status == "installed"
    assert download_status.installed_files == 2
    assert download_status.installed_bytes == len(content_a) + len(content_b)

    is_valid, errors = manager.verify()
    assert is_valid is True
    assert errors == []


def test_model_manager_detects_corrupted_file(tmp_path: Path):
    content_a = b"correct-weights"
    hash_a = _content_hash(content_a)

    mini_manifest = ModelPackageManifest(
        name="test-ocr",
        version="1.0.0",
        license="Apache-2.0",
        description="Test models",
        language="en",
        backend="cpu",
        files=(
            ModelFile("model_a", "net/model.bin", hash_a, len(content_a), "https://example.com/a"),
        ),
    )

    manager = OcrModelManager(tmp_path, manifest=mini_manifest)
    target_file = manager.package_dir / "net" / "model.bin"
    target_file.parent.mkdir(parents=True)
    target_file.write_bytes(b"tampered-content")

    status = manager.get_status()
    assert status.status == "corrupted"


def test_model_manager_repairs_corrupted_file(tmp_path: Path):
    content_a = b"correct-weights-123"
    hash_a = _content_hash(content_a)

    mini_manifest = ModelPackageManifest(
        name="test-ocr",
        version="1.0.0",
        license="Apache-2.0",
        description="Test models",
        language="en",
        backend="cpu",
        files=(
            ModelFile("model_a", "net/model.bin", hash_a, len(content_a), "https://example.com/a"),
        ),
    )

    def fake_downloader(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content_a)

    manager = OcrModelManager(tmp_path, manifest=mini_manifest, downloader=fake_downloader)
    target_file = manager.package_dir / "net" / "model.bin"
    target_file.parent.mkdir(parents=True)
    target_file.write_bytes(b"corrupt-data")

    assert manager.get_status().status == "corrupted"

    repair_status = manager.repair_package()
    assert repair_status.status == "installed"
    assert target_file.read_bytes() == content_a


def test_model_manager_remove_package(tmp_path: Path):
    manifest = ModelPackageManifest(
        name="test-ocr",
        version="1.0.0",
        license="Apache-2.0",
        description="Test",
        language="en",
        backend="cpu",
        files=(),
    )
    manager = OcrModelManager(tmp_path, manifest=manifest)
    manager.package_dir.mkdir(parents=True)
    (manager.package_dir / "sample.txt").write_text("ok")

    assert manager.remove_package() is True
    assert not manager.package_dir.exists()


def test_insufficient_disk_space_raises_error(tmp_path: Path, monkeypatch):
    import shutil

    mini_manifest = ModelPackageManifest(
        name="test-ocr",
        version="1.0.0",
        license="Apache-2.0",
        description="Test",
        language="en",
        backend="cpu",
        files=(
            ModelFile("huge", "huge.bin", "abc", 100 * 1024 * 1024 * 1024, "https://example.com/huge"),
        ),
    )

    # Mock disk_usage to report 10 MB free
    monkeypatch.setattr(shutil, "disk_usage", lambda _path: (1000, 500, 10 * 1024 * 1024))
    manager = OcrModelManager(tmp_path, manifest=mini_manifest)

    with pytest.raises(InsufficientDiskSpaceError):
        manager.download_package()
