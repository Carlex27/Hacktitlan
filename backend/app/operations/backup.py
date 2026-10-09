"""Verified local backup. Restore is intentionally not exposed through HTTP."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import Settings, get_settings
from backend.app.infrastructure.database.models import BackupRun, StoredFile
from backend.app.infrastructure.database.session import create_database_engine, create_session_factory
from backend.app.infrastructure.files import FileStorage
from backend.app.operations.backup_archive import file_hash, verify_archive


class SecondaryBackupError(RuntimeError):
    def __init__(self, result: dict, cause: Exception) -> None:
        super().__init__(f"Respaldo primario verificado; segunda copia falló: {cause}")
        self.result = result


class BackupService:
    retention = {"daily": 7, "weekly": 4, "monthly": 12, "manual": 3}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        roots = [settings.storage_root.resolve(), settings.backup_root.resolve()]
        if settings.secondary_backup_root:
            roots.append(settings.secondary_backup_root.resolve())
        for index, root in enumerate(roots):
            for other in roots[index + 1:]:
                if root.is_relative_to(other) or other.is_relative_to(root):
                    raise ValueError("Almacenamiento y respaldos requieren carpetas independientes")

    def create(self, kind: str = "daily") -> dict[str, Any]:
        if kind not in self.retention:
            raise ValueError("Backup kind must be daily, weekly, monthly or manual")
        self.settings.backup_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destination = self.settings.backup_root / f"backup_{kind}_{timestamp}.zip"
        with tempfile.TemporaryDirectory(dir=self.settings.backup_root) as temporary_name:
            temporary = Path(temporary_name)
            dump_path = temporary / "database.dump"
            counts, stored_files = self._snapshot_dump(dump_path)
            listing_path = temporary / "database.restore-list.txt"
            self._verify_dump(dump_path, listing_path)
            files = [dump_path, listing_path]
            archive_sources: list[tuple[Path, Path]] = [(item, Path(item.name)) for item in files]
            if self.settings.storage_root.exists():
                for source in self.settings.storage_root.rglob("*"):
                    if source.is_file() and ".tmp" not in source.parts:
                        archive_sources.append(
                            (source, Path("storage") / source.relative_to(self.settings.storage_root))
                        )
            storage = FileStorage(self.settings.storage_root, self.settings.max_pdf_bytes)
            for relative_path, expected_hash in stored_files:
                if file_hash(storage.resolve(relative_path)) != expected_hash:
                    raise RuntimeError(f"El archivo administrado no coincide con su hash: {relative_path}")
            project_root = Path(__file__).resolve().parents[3]
            rule_sources = [project_root / "docs" / "CERTIFICATE_EXTRACTION_RULES.md"]
            ligie_root = project_root / "data" / "ligie" / "chapter-72" / "source-provided"
            if ligie_root.exists():
                rule_sources.extend(item for item in ligie_root.rglob("*") if item.is_file())
            for rule_source in rule_sources:
                if rule_source.is_file():
                    archive_sources.append((rule_source, Path("rules") / rule_source.relative_to(project_root)))
            manifest = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "kind": kind,
                "database_format": "pg_dump custom",
                "table_counts": counts,
                "components": [
                    {
                        "path": archive_name.as_posix(),
                        "size_bytes": source.stat().st_size,
                        "sha256": file_hash(source),
                    }
                    for source, archive_name in archive_sources
                ],
            }
            hashes = {item["path"]: item["sha256"] for item in manifest["components"]}
            for relative_path, expected_hash in stored_files:
                if hashes.get(f"storage/{relative_path}") != expected_hash:
                    raise RuntimeError(f"El respaldo omite o altera un archivo administrado: {relative_path}")
            (temporary / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            pending = temporary / "backup.zip.partial"
            with ZipFile(pending, "w", ZIP_DEFLATED, allowZip64=True) as archive:
                archive.write(temporary / "manifest.json", "manifest.json")
                for source, archive_name in archive_sources:
                    archive.write(source, archive_name)
            verify_archive(pending)
            with pending.open("r+b") as stream:
                os.fsync(stream.fileno())
            os.replace(pending, destination)
        archive_hash = file_hash(destination)
        result = {
            "path": str(destination),
            "secondary_path": None,
            "sha256": archive_hash,
            "verified": True,
            "manifest": manifest,
        }
        try:
            if self.settings.secondary_backup_root:
                result["secondary_path"] = str(self.copy_secondary(destination))
        except Exception as exc:
            raise SecondaryBackupError(result, exc) from exc
        self._apply_retention(kind)
        return result

    def copy_secondary(self, source: Path) -> Path:
        if self.settings.secondary_backup_root is None:
            raise ValueError("No se configuró la segunda copia")
        source = source.resolve()
        if source.parent != self.settings.backup_root.resolve():
            raise ValueError("El respaldo debe pertenecer a la carpeta primaria")
        verify_archive(source)
        root = self.settings.secondary_backup_root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(root).free < source.stat().st_size:
            raise OSError("Espacio insuficiente para la segunda copia")
        destination = root / source.name
        pending = root / f".{source.name}.{uuid4().hex}.partial"
        try:
            shutil.copy2(source, pending)
            if file_hash(pending) != file_hash(source):
                raise RuntimeError("La segunda copia no coincide con el respaldo primario")
            with pending.open("r+b") as stream:
                os.fsync(stream.fileno())
            os.replace(pending, destination)
        finally:
            pending.unlink(missing_ok=True)
        return destination

    def retry_secondary(self, sessions: sessionmaker[Session], source: Path) -> dict:
        source = source.resolve()
        digest = file_hash(source)
        with sessions() as session:
            records = session.scalars(select(BackupRun).where(BackupRun.primary_path == str(source))).all()
            if any(record.sha256 != digest for record in records):
                raise RuntimeError("El respaldo primario cambió desde su registro")
        destination = self.copy_secondary(source)
        with sessions.begin() as session:
            for record in session.scalars(select(BackupRun).where(BackupRun.primary_path == str(source))):
                record.secondary_path = str(destination)
                record.status = "verified"
                record.error_message = None
                record.finished_at = datetime.now(timezone.utc)
        kind = verify_archive(source)["kind"]
        self._apply_retention(kind)
        return {"path": str(source), "secondary_path": str(destination), "verified": True}

    def scheduled_kinds(self, now: datetime) -> list[str]:
        kinds = ["daily"]
        for kind in ("weekly", "monthly"):
            current = False
            for path in self.settings.backup_root.glob(f"backup_{kind}_*.zip"):
                match = re.fullmatch(r"backup_\w+_(\d{8}T\d{6})\d*Z\.zip", path.name)
                if not match:
                    continue
                created = datetime.strptime(match[1], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc).astimezone(now.tzinfo)
                current = (created.isocalendar()[:2] == now.isocalendar()[:2] if kind == "weekly"
                           else (created.year, created.month) == (now.year, now.month))
                if current:
                    break
            if not current:
                kinds.append(kind)
        return kinds

    def _snapshot_dump(self, destination: Path) -> tuple[dict[str, int], list[tuple[str, str]]]:
        engine = create_database_engine(self.settings)
        try:
            with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
                with connection.begin():
                    snapshot = connection.scalar(text("SELECT pg_export_snapshot()"))
                    counts = {name: connection.scalar(text(
                        f'SELECT count(*) FROM public.{connection.dialect.identifier_preparer.quote(name)}'
                    )) for name in inspect(connection).get_table_names(schema="public")}
                    files = [(row.relative_path, row.sha256)
                             for row in connection.execute(select(StoredFile.relative_path, StoredFile.sha256))]
                    self._dump_database(destination, snapshot)
            return counts, files
        finally:
            engine.dispose()

    def create_and_record(
        self, sessions: sessionmaker[Session], kind: str = "daily"
    ) -> dict[str, Any]:
        with sessions.begin() as session:
            run = BackupRun(
                status="running",
                kind=kind,
                started_at=datetime.now(timezone.utc),
            )
            session.add(run)
            session.flush()
            run_id = run.id
        try:
            result = self.create(kind)
        except Exception as exc:
            with sessions.begin() as session:
                run = session.get(BackupRun, run_id)
                if run:
                    run.status = "failed"
                    if isinstance(exc, SecondaryBackupError):
                        run.primary_path = exc.result["path"]
                        run.sha256 = exc.result["sha256"]
                        run.manifest_json = exc.result["manifest"]
                    run.error_message = str(exc)[:4000]
                    run.finished_at = datetime.now(timezone.utc)
            raise
        with sessions.begin() as session:
            run = session.get(BackupRun, run_id)
            if run:
                run.status = "verified"
                run.primary_path = result["path"]
                run.secondary_path = result["secondary_path"]
                run.sha256 = result["sha256"]
                run.manifest_json = result["manifest"]
                run.finished_at = datetime.now(timezone.utc)
        return {**result, "backup_run_id": run_id}

    def _database_command(self, executable: str) -> tuple[list[str], dict[str, str]]:
        url = make_url(self.settings.database_url)
        command = [executable]
        if url.host:
            command += ["--host", url.host]
        if url.port:
            command += ["--port", str(url.port)]
        if url.username:
            command += ["--username", url.username]
        command += ["--dbname", url.database or "hacktitlan"]
        environment = os.environ.copy()
        if url.password:
            environment["PGPASSWORD"] = url.password
        return command, environment

    def _dump_database(self, destination: Path, snapshot: str) -> None:
        command, environment = self._database_command("pg_dump")
        command += ["--format=custom", "--snapshot", snapshot, "--file", str(destination)]
        subprocess.run(command, env=environment, check=True, capture_output=True, text=True)

    def _verify_dump(self, dump_path: Path, listing_path: Path) -> None:
        result = subprocess.run(
            ["pg_restore", "--list", str(dump_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        if not result.stdout.strip():
            raise RuntimeError("pg_restore no encontró objetos en el respaldo")
        listing_path.write_text(result.stdout, encoding="utf-8")

    def _apply_retention(self, kind: str) -> None:
        roots = [self.settings.backup_root]
        if self.settings.secondary_backup_root:
            roots.append(self.settings.secondary_backup_root)
        for root in roots:
            backups = sorted(
                root.glob(f"backup_{kind}_*.zip"),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
            for expired in backups[self.retention[kind] :]:
                expired.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and verify a complete local backup")
    parser.add_argument("--kind", choices=["daily", "weekly", "monthly", "manual"])
    parser.add_argument("--retry-secondary", type=Path, help="Reintentar copia de un ZIP primario verificado")
    arguments = parser.parse_args()
    settings = get_settings()
    service = BackupService(settings)
    sessions = create_session_factory(settings)
    if arguments.retry_secondary:
        print(json.dumps(service.retry_secondary(sessions, arguments.retry_secondary)))
        return
    if arguments.kind:
        print(json.dumps([service.create_and_record(sessions, arguments.kind)], ensure_ascii=False))
        return
    now = datetime.now().astimezone()
    results = [service.create_and_record(sessions, kind) for kind in service.scheduled_kinds(now)]
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
