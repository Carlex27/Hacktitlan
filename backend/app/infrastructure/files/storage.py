"""Content-addressed, atomic storage for source and generated files."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import tempfile
from typing import BinaryIO

from backend.app.domain.errors import ApplicationError
from backend.app.document_ingestion.excel_reader import validate_xlsx


@dataclass(frozen=True)
class StoredArtifact:
    sha256: str
    original_name: str
    storage_name: str
    relative_path: str
    media_type: str
    size_bytes: int
    duplicate: bool


class FileStorage:
    def __init__(self, root: Path, max_pdf_bytes: int) -> None:
        self.root = root.resolve()
        self.max_pdf_bytes = max_pdf_bytes
        self.temp_root = self.root / ".tmp"
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def store_pdf(self, stream: BinaryIO, original_name: str) -> StoredArtifact:
        if Path(original_name).suffix.lower() != ".pdf":
            raise ApplicationError("invalid_file_type", "El archivo debe tener extensión .pdf")
        return self.store_document(stream, original_name)

    def store_document(self, stream: BinaryIO, original_name: str) -> StoredArtifact:
        safe_name = Path(original_name or "document.pdf").name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in {".pdf", ".xlsx"}:
            raise ApplicationError("invalid_file_type", "El archivo debe tener extensión .pdf o .xlsx")

        digest = sha256()
        size = 0
        first_bytes = b""
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".upload", dir=self.temp_root, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                while chunk := stream.read(1024 * 1024):
                    if not first_bytes:
                        first_bytes = chunk[:5]
                    size += len(chunk)
                    if size > self.max_pdf_bytes:
                        raise ApplicationError(
                            "file_too_large",
                            f"El archivo excede el límite de {self.max_pdf_bytes} bytes",
                            status_code=413,
                        )
                    digest.update(chunk)
                    temporary.write(chunk)
                temporary.flush()
                os.fsync(temporary.fileno())

            if suffix == ".pdf" and (size == 0 or first_bytes != b"%PDF-"):
                raise ApplicationError("invalid_pdf", "El archivo no contiene una cabecera PDF válida")
            if suffix == ".xlsx":
                validate_xlsx(temporary_path)

            hash_value = digest.hexdigest()
            verification = sha256()
            with temporary_path.open("rb") as written:
                while verification_chunk := written.read(1024 * 1024):
                    verification.update(verification_chunk)
            if verification.hexdigest() != hash_value:
                raise ApplicationError(
                    "storage_hash_mismatch",
                    "El archivo temporal no coincide con su hash calculado",
                    status_code=500,
                )
            relative = Path(hash_value[:2]) / hash_value[2:4] / f"{hash_value}{suffix}"
            final_path = self.root / relative
            final_path.parent.mkdir(parents=True, exist_ok=True)
            duplicate = final_path.exists()
            if duplicate:
                temporary_path.unlink(missing_ok=True)
            else:
                os.replace(temporary_path, final_path)
            return StoredArtifact(
                sha256=hash_value,
                original_name=safe_name,
                storage_name=final_path.name,
                relative_path=relative.as_posix(),
                media_type="application/pdf" if suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                size_bytes=size,
                duplicate=duplicate,
            )
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / Path(relative_path)).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ApplicationError("invalid_storage_path", "Ruta de almacenamiento inválida") from exc
        if not candidate.is_file():
            raise ApplicationError("stored_file_missing", "El archivo almacenado no está disponible", status_code=404)
        return candidate

    def store_generated(
        self, source: Path, original_name: str, media_type: str
    ) -> StoredArtifact:
        if not source.is_file():
            raise ApplicationError("generated_file_missing", "El archivo generado no existe")
        safe_name = Path(original_name).name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in {".xlsx", ".csv", ".pdf", ".zip"}:
            raise ApplicationError("invalid_generated_type", "Tipo de archivo generado no permitido")
        digest = sha256()
        size = 0
        with source.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        hash_value = digest.hexdigest()
        relative = Path("generated") / hash_value[:2] / f"{hash_value}{suffix}"
        final_path = self.root / relative
        final_path.parent.mkdir(parents=True, exist_ok=True)
        duplicate = final_path.exists()
        if not duplicate:
            temporary_path = self.temp_root / f"{hash_value}{suffix}.tmp"
            try:
                with source.open("rb") as input_stream, temporary_path.open("wb") as output_stream:
                    while chunk := input_stream.read(1024 * 1024):
                        output_stream.write(chunk)
                    output_stream.flush()
                    os.fsync(output_stream.fileno())
                verification = sha256()
                with temporary_path.open("rb") as written:
                    while verification_chunk := written.read(1024 * 1024):
                        verification.update(verification_chunk)
                if verification.hexdigest() != hash_value:
                    raise ApplicationError("storage_hash_mismatch", "El archivo generado no superó la verificación")
                os.replace(temporary_path, final_path)
            finally:
                temporary_path.unlink(missing_ok=True)
        return StoredArtifact(
            sha256=hash_value,
            original_name=safe_name,
            storage_name=final_path.name,
            relative_path=relative.as_posix(),
            media_type=media_type,
            size_bytes=size,
            duplicate=duplicate,
        )
