from collections import namedtuple
from hashlib import sha256
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from backend.app.config import Settings
from backend.app.operations.backup import BackupService, SecondaryBackupError
from backend.app.operations.backup_archive import file_hash, verify_archive


@pytest.fixture
def service(tmp_path, monkeypatch):
    settings = Settings(storage_root=tmp_path / "storage", backup_root=tmp_path / "backups",
                        secondary_backup_root=tmp_path / "secondary")
    settings.storage_root.mkdir()
    pdf = settings.storage_root / "source.pdf"
    pdf.write_bytes(b"%PDF-1.7\nbackup fixture")
    expected_hash = file_hash(pdf)
    (settings.storage_root / "derived.xlsx").write_bytes(b"derived fixture")
    (settings.storage_root / ".tmp").mkdir()
    (settings.storage_root / ".tmp" / "partial.upload").write_bytes(b"incomplete")
    instance = BackupService(settings)
    def fake_dump(destination):
        destination.write_bytes(b"database fixture")
        return {"documents": 1}, [("source.pdf", expected_hash)]
    monkeypatch.setattr(instance, "_snapshot_dump", fake_dump)
    monkeypatch.setattr(instance, "_verify_dump", lambda dump, listing: listing.write_text("objects"))
    return instance


def test_backup_publishes_verified_archive_and_second_copy(service):
    result = service.create("manual")
    manifest = verify_archive(Path(result["path"]))
    assert manifest["table_counts"] == {"documents": 1}
    paths = [item["path"] for item in manifest["components"]]
    assert "storage/source.pdf" in paths
    assert "storage/derived.xlsx" in paths
    assert any(path.startswith("rules/") for path in paths)
    assert not any(".tmp" in path for path in paths)
    assert file_hash(Path(result["secondary_path"])) == result["sha256"]
    second = service.create("manual")
    assert second["path"] != result["path"]


@pytest.mark.parametrize("kind,limit", [("daily", 7), ("weekly", 4), ("monthly", 12)])
def test_retention_keeps_independent_buckets_on_both_copies(service, kind, limit):
    for root in (service.settings.backup_root, service.settings.secondary_backup_root):
        root.mkdir()
        for number in range(limit + 3):
            (root / f"backup_{kind}_{number:03}.zip").write_bytes(b"backup")
        (root / "backup_manual_preserved.zip").write_bytes(b"manual")
    service._apply_retention(kind)
    for root in (service.settings.backup_root, service.settings.secondary_backup_root):
        assert len(list(root.glob(f"backup_{kind}_*.zip"))) == limit
        assert (root / "backup_manual_preserved.zip").exists()


def test_secondary_without_space_preserves_primary_and_can_recover(service, monkeypatch):
    import backend.app.operations.backup as backup
    original_usage = backup.shutil.disk_usage
    monkeypatch.setattr(backup.shutil, "disk_usage", lambda root: namedtuple("Usage", "total used free")(1, 1, 0))
    with pytest.raises(SecondaryBackupError) as error:
        service.create()
    primary = Path(error.value.result["path"])
    assert verify_archive(primary)
    assert not list(service.settings.secondary_backup_root.glob("*.zip"))
    assert not list(service.settings.secondary_backup_root.glob("*.partial"))
    monkeypatch.setattr(backup.shutil, "disk_usage", original_usage)
    assert file_hash(service.copy_secondary(primary)) == file_hash(primary)


def test_absent_secondary_preserves_primary(service, monkeypatch):
    original_mkdir = Path.mkdir
    def fail_secondary(path, *args, **kwargs):
        if path == service.settings.secondary_backup_root:
            raise FileNotFoundError("Unidad secundaria desconectada")
        return original_mkdir(path, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", fail_secondary)
    with pytest.raises(SecondaryBackupError) as error:
        service.create()
    assert Path(error.value.result["path"]).is_file()


def test_corrupt_second_copy_is_not_published(service, monkeypatch):
    import backend.app.operations.backup as backup
    monkeypatch.setattr(backup.shutil, "copy2", lambda source, target: target.write_bytes(b"corrupt"))
    with pytest.raises(SecondaryBackupError, match="no coincide"):
        service.create()
    assert not list(service.settings.secondary_backup_root.iterdir())


def test_altered_managed_file_prevents_publication(service):
    (service.settings.storage_root / "source.pdf").unlink()
    with pytest.raises(Exception, match="no está disponible"):
        service.create()
    assert not list(service.settings.backup_root.glob("*.zip"))


@pytest.mark.parametrize("name", ["../escape", "C:/escape", "storage\\escape", "/absolute", "storage/./escape"])
def test_archive_rejects_unsafe_paths(tmp_path, name):
    path = tmp_path / "unsafe.zip"
    with ZipFile(path, "w") as archive:
        entry = ZipInfo("entry")
        entry.filename = name
        archive.writestr(entry, b"bad")
    with pytest.raises(ValueError, match="insegura"):
        verify_archive(path)


def test_archive_rejects_changed_content(tmp_path):
    path = tmp_path / "tampered.zip"
    manifest = {"components": [{"path": "database.dump", "size_bytes": 4, "sha256": sha256(b"good").hexdigest()}]}
    with ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("database.dump", b"evil")
    with pytest.raises(ValueError, match="Hash"):
        verify_archive(path)


def test_backup_task_catches_missed_runs_and_propagates_failures():
    scripts = Path(__file__).resolve().parents[3] / "scripts"
    install = (scripts / "install-backup-task.ps1").read_text()
    run = (scripts / "run-backup.ps1").read_text()
    assert "-At 2am" in install
    assert "-StartWhenAvailable" in install
    assert "-MultipleInstances IgnoreNew" in install
    assert "exit $LASTEXITCODE" in run


def test_schedule_recovers_missed_weekly_and_monthly_slots_in_local_time(service):
    mexico = timezone(timedelta(hours=-6))
    now = datetime(2026, 10, 8, 2, tzinfo=mexico)
    assert service.scheduled_kinds(now) == ["daily", "weekly", "monthly"]
    service.settings.backup_root.mkdir()
    # These completed archives cover the current week and month even after a missed Monday/first day.
    for kind in ("weekly", "monthly"):
        (service.settings.backup_root / f"backup_{kind}_20261006T080000000001Z.zip").write_bytes(b"fixture")
    assert service.scheduled_kinds(now) == ["daily"]
    assert service.scheduled_kinds(datetime(2026, 11, 2, 2, tzinfo=mexico)) == ["daily", "weekly", "monthly"]
