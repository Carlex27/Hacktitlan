"""Typed runtime configuration for the central backend."""

from __future__ import annotations

from functools import lru_cache
import socket
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HACKTITLAN_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    database_url: str = "postgresql+psycopg://hacktitlan_app:change-me@127.0.0.1:5432/hacktitlan"
    storage_root: Path = Path(r"C:\ProgramData\Hacktitlan\storage")
    backup_root: Path = Path(r"C:\ProgramData\Hacktitlan\backups")
    secondary_backup_root: Path | None = None
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8765, ge=1, le=65535)
    max_pdf_bytes: int = Field(default=100 * 1024 * 1024, ge=1024)
    workstation_name: str = Field(default_factory=socket.gethostname)
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)
    database_statement_timeout_ms: int = Field(default=30_000, ge=1_000)
    worker_poll_seconds: float = Field(default=2.0, ge=0.1)
    worker_stale_after_seconds: int = Field(default=300, ge=30)
    demo_notice: str = "DEMOSTRACIÓN — SIN VALIDEZ ADUANERA"

    @field_validator("secondary_backup_root", mode="before")
    @classmethod
    def empty_secondary_path_is_none(cls, value):
        return None if value is None or str(value).strip() == "" else value

    @field_validator("workstation_name", mode="before")
    @classmethod
    def default_blank_workstation(cls, value):
        return socket.gethostname() if value is None or str(value).strip() == "" else value

    @model_validator(mode="after")
    def backup_locations_are_distinct(self):
        if self.backup_root.resolve() == self.storage_root.resolve():
            raise ValueError("La carpeta de respaldo debe ser distinta del almacenamiento")
        if self.secondary_backup_root is not None:
            secondary = self.secondary_backup_root.resolve()
            if secondary in {self.backup_root.resolve(), self.storage_root.resolve()}:
                raise ValueError("La segunda copia debe usar una carpeta distinta")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

