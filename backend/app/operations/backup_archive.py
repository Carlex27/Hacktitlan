"""Streaming integrity checks for local backup archives."""

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive(path: Path) -> dict:
    with ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("El respaldo contiene rutas duplicadas")
        for info in archive.infolist():
            name = info.orig_filename
            relative = PurePosixPath(name)
            if (relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name
                    or relative.as_posix() != name):
                raise ValueError("El respaldo contiene una ruta insegura")
        manifest = json.loads(archive.read("manifest.json"))
        components = manifest["components"]
        expected = [item["path"] for item in components]
        if len(expected) != len(set(expected)) or set(names) != {"manifest.json", *expected}:
            raise ValueError("El contenido del respaldo no coincide con el manifiesto")
        if "database.dump" not in expected:
            raise ValueError("El respaldo no contiene la base de datos")
        for item in components:
            info = archive.getinfo(item["path"])
            if info.file_size != item["size_bytes"]:
                raise ValueError(f"Tamaño incorrecto: {item['path']}")
            digest = sha256()
            with archive.open(info) as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != item["sha256"]:
                raise ValueError(f"Hash incorrecto: {item['path']}")
    return manifest
