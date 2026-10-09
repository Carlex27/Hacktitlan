from pathlib import Path
import shutil

import pytest
from sqlalchemy import create_engine, select, text

from backend.app.config import Settings
from backend.app.infrastructure.database.models import BackupRun
from backend.app.infrastructure.database.session import create_session_factory
from backend.app.infrastructure.files import FileStorage
from backend.app.operations.backup import BackupService, SecondaryBackupError
from backend.app.operations.backup_archive import file_hash, verify_archive
from backend.app.operations.restore import restore_backup
from backend.app.operations.volume_seed import migrate, seed_volume, temporary_database


def test_real_backup_restore_compares_counts_and_files_and_records_secondary_failure(tmp_path, monkeypatch):
    base = Settings()
    if not base.test_database_url or not all(shutil.which(tool) for tool in ("pg_dump", "pg_restore")):
        pytest.skip("Requires hacktitlan_test credentials and PostgreSQL utilities in PATH")
    with temporary_database(base, tmp_path / "source") as source:
        migrate(source)
        assert seed_volume(source, certificates=12, heats_per_certificate=15)["heats"] == 180
        derived = tmp_path / "report.csv"
        derived.write_text("certificate,value\n1,3\n")
        artifact = FileStorage(source.storage_root, source.max_pdf_bytes).store_generated(derived, "report.csv", "text/csv")
        engine = create_engine(source.database_url)
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO stored_files(sha256,original_name,storage_name,
                relative_path,media_type,size_bytes,status) VALUES (:hash,'report.csv',:name,:path,'text/csv',:size,'ready')"""),
                {"hash": artifact.sha256, "name": artifact.storage_name, "path": artifact.relative_path, "size": artifact.size_bytes})
        engine.dispose()
        service = BackupService(source)
        sessions = create_session_factory(source)
        original_dump = service._dump_database
        def concurrent_dump(destination, snapshot):
            concurrent_engine = create_engine(source.database_url)
            try:
                with concurrent_engine.begin() as connection:
                    connection.execute(text("INSERT INTO manufacturers(name,normalized_name) VALUES ('After snapshot','after snapshot')"))
                original_dump(destination, snapshot)
            finally:
                concurrent_engine.dispose()
        monkeypatch.setattr(service, "_dump_database", concurrent_dump)
        original_copy = service.copy_secondary
        monkeypatch.setattr(service, "copy_secondary", lambda path: (_ for _ in ()).throw(OSError("disconnected")))
        with pytest.raises(SecondaryBackupError) as failure:
            service.create_and_record(sessions)
        with sessions() as session:
            failed = session.scalar(select(BackupRun))
            assert failed.status == "failed"
            assert failed.primary_path == failure.value.result["path"]
            assert failed.sha256 == file_hash(Path(failed.primary_path))
            assert failed.manifest_json["table_counts"]["heats"] == 180
            assert failed.manifest_json["table_counts"]["manufacturers"] == 20
        monkeypatch.setattr(service, "_dump_database", original_dump)
        monkeypatch.setattr(service, "copy_secondary", original_copy)
        recovered = service.retry_secondary(sessions, Path(failure.value.result["path"]))
        assert recovered["verified"]
        with sessions() as session:
            assert session.scalar(select(BackupRun)).status == "verified"
        result = service.create_and_record(sessions, "manual")
        assert file_hash(Path(result["secondary_path"])) == result["sha256"]
        assert verify_archive(Path(result["path"]))["table_counts"]["mill_certificates"] == 12
        with temporary_database(base, tmp_path / "restored") as target:
            restored = restore_backup(target, Path(result["path"]), target.storage_root, tmp_path / "rules")
            assert restored["verified"]
            assert restored["table_counts"] == result["manifest"]["table_counts"]
            assert file_hash(target.storage_root / artifact.relative_path) == artifact.sha256
            with pytest.raises(ValueError, match="vacías"):
                restore_backup(target, Path(result["path"]), target.storage_root, tmp_path / "rules")
            with pytest.raises(ValueError, match="base vacía"):
                restore_backup(target, Path(result["path"]), tmp_path / "empty-storage", tmp_path / "empty-rules")
        sessions.kw["bind"].dispose()


def test_volume_seed_rejects_production_database(tmp_path):
    with pytest.raises(ValueError, match="desechable"):
        seed_volume(Settings(storage_root=tmp_path / "storage"), certificates=1)
