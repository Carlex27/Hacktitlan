"""Local restoration into an existing empty database and empty destinations."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from sqlalchemy import inspect, text

from backend.app.config import Settings, get_settings
from backend.app.infrastructure.database.session import create_database_engine
from backend.app.operations.backup import BackupService
from backend.app.operations.backup_archive import file_hash, verify_archive


def restore_backup(settings: Settings, archive_path: Path, storage_root: Path, rules_root: Path) -> dict:
    manifest = verify_archive(archive_path)
    if not isinstance(manifest.get("table_counts"), dict) or not manifest["table_counts"]:
        raise ValueError("El respaldo no contiene conteos verificables de la base")
    roots = [storage_root.resolve(), rules_root.resolve()]
    if roots[0].is_relative_to(roots[1]) or roots[1].is_relative_to(roots[0]):
        raise ValueError("Las carpetas de restauración deben ser independientes")
    for root in roots:
        if root.exists() and (not root.is_dir() or any(root.iterdir())):
            raise ValueError("La restauración requiere carpetas vacías")
    engine = create_database_engine(settings)
    try:
        with engine.connect() as connection:
            if inspect(connection).get_table_names(schema="public"):
                raise ValueError("La restauración requiere una base vacía")
        with tempfile.TemporaryDirectory() as temporary_name:
            temporary = Path(temporary_name)
            with ZipFile(archive_path) as archive:
                archive.extractall(temporary)
            # Files are staged before the transactional database restore; originals are never overwritten.
            for folder, root in zip(("storage", "rules"), roots):
                root.mkdir(parents=True, exist_ok=True)
                source = temporary / folder
                if source.exists():
                    shutil.copytree(source, root, dirs_exist_ok=True)
            command, environment = BackupService(settings)._database_command("pg_restore")
            command += ["--single-transaction", "--exit-on-error", "--no-owner", "--no-privileges",
                        str(temporary / "database.dump")]
            subprocess.run(command, env=environment, check=True, capture_output=True, text=True)
        with engine.connect() as connection:
            counts = {name: connection.scalar(text(
                f'SELECT count(*) FROM public.{connection.dialect.identifier_preparer.quote(name)}'
            )) for name in inspect(connection).get_table_names(schema="public")}
        if manifest.get("table_counts") is None or counts != manifest["table_counts"]:
            raise RuntimeError("Los conteos restaurados no coinciden con el manifiesto")
        for item in manifest["components"]:
            parts = Path(item["path"]).parts
            if parts[0] in {"storage", "rules"}:
                root = roots[0] if parts[0] == "storage" else roots[1]
                if file_hash(root.joinpath(*parts[1:])) != item["sha256"]:
                    raise RuntimeError(f"Hash restaurado incorrecto: {item['path']}")
        return {"verified": True, "table_counts": counts,
                "storage_root": str(roots[0]), "rules_root": str(roots[1])}
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Restaurar un respaldo confiable en una base vacía")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--rules-root", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(restore_backup(get_settings(), arguments.archive,
                                   arguments.storage_root, arguments.rules_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
