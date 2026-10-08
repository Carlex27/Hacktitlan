"""Verified local backup. Restore is intentionally not exposed through HTTP."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import Settings, get_settings
from backend.app.infrastructure.database.models import BackupRun
from backend.app.infrastructure.database.session import create_session_factory


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class BackupService:
    retention = {"daily": 7, "weekly": 4, "monthly": 12, "manual": 3}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self, kind: str = "daily") -> dict[str, Any]:
        if kind not in self.retention:
            raise ValueError("Backup kind must be daily, weekly, monthly or manual")
        self.settings.backup_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = self.settings.backup_root / f"backup_{kind}_{timestamp}.zip"
        with tempfile.TemporaryDirectory(dir=self.settings.backup_root) as temporary_name:
            temporary = Path(temporary_name)
            dump_path = temporary / "database.dump"
            self._dump_database(dump_path)
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
            rule_sources = [Path("docs") / "CERTIFICATE_EXTRACTION_RULES.md"]
            ligie_root = Path("data") / "ligie" / "chapter-72" / "source-provided"
            if ligie_root.exists():
                rule_sources.extend(item for item in ligie_root.rglob("*") if item.is_file())
            for rule_source in rule_sources:
                if rule_source.is_file():
                    archive_sources.append((rule_source, Path("rules") / rule_source.as_posix()))
            manifest = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "kind": kind,
                "database_format": "pg_dump custom",
                "components": [
                    {
                        "path": archive_name.as_posix(),
                        "size_bytes": source.stat().st_size,
                        "sha256": file_hash(source),
                    }
                    for source, archive_name in archive_sources
                ],
            }
            (temporary / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            with ZipFile(destination, "w", ZIP_DEFLATED, allowZip64=True) as archive:
                archive.write(temporary / "manifest.json", "manifest.json")
                for source, archive_name in archive_sources:
                    archive.write(source, archive_name)
        archive_hash = file_hash(destination)
        secondary = None
        if self.settings.secondary_backup_root:
            secondary_root = self.settings.secondary_backup_root.resolve()
            secondary_root.mkdir(parents=True, exist_ok=True)
            secondary = secondary_root / destination.name
            shutil.copy2(destination, secondary)
            if file_hash(secondary) != archive_hash:
                raise RuntimeError("La segunda copia no coincide con el respaldo primario")
        self._apply_retention(kind)
        return {
            "path": str(destination),
            "secondary_path": str(secondary) if secondary else None,
            "sha256": archive_hash,
            "verified": True,
        }

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
                run.manifest_json = {"verified": True}
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

    def _dump_database(self, destination: Path) -> None:
        command, environment = self._database_command("pg_dump")
        command += ["--format=custom", "--file", str(destination)]
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
    arguments = parser.parse_args()
    settings = get_settings()
    service = BackupService(settings)
    sessions = create_session_factory(settings)
    if arguments.kind:
        print(json.dumps([service.create_and_record(sessions, arguments.kind)], ensure_ascii=False))
        return
    now = datetime.now(timezone.utc)
    results = [service.create_and_record(sessions, "daily")]
    if now.weekday() == 0:
        results.append(service.create_and_record(sessions, "weekly"))
    if now.day == 1:
        results.append(service.create_and_record(sessions, "monthly"))
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
