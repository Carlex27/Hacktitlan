from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "ligie"
    / "chapter-72"
    / "source-provided"
    / "catalog.json"
)
EXPECTED_CATALOG_SHA256 = "c5fa60696c42187a31dec6dc7ad8e545a751642e04ae3593c0cf0d3d246b4a2b"


def compact_code(value: str) -> str:
    return value.replace(".", "").replace("-", "")


@dataclass(frozen=True)
class CatalogEntry:
    kind: str
    code: str
    description: str
    page: int | None
    raw: dict[str, Any]


class SourceProvidedCatalog:
    def __init__(
        self,
        path: Path = DEFAULT_CATALOG_PATH,
        expected_sha256: str | None = EXPECTED_CATALOG_SHA256,
    ) -> None:
        raw = path.read_bytes()
        actual_hash = sha256(raw).hexdigest()
        if expected_sha256 is not None and actual_hash != expected_sha256:
            raise ValueError(
                "The source-provided catalog changed without a rule-version update"
            )
        payload = json.loads(raw.decode("utf-8"))
        self.path = path
        self.sha256 = actual_hash
        self.entries = tuple(
            CatalogEntry(
                kind=str(item.get("type") or ""),
                code=compact_code(str(item.get("code") or "")),
                description=str(item.get("description") or ""),
                page=item.get("page"),
                raw=item,
            )
            for item in payload
            if item.get("code")
        )
        grouped: dict[str, list[CatalogEntry]] = {}
        for entry in self.entries:
            grouped.setdefault(entry.code, []).append(entry)
        self._by_code = {code: tuple(entries) for code, entries in grouped.items()}

    def get(self, code: str) -> CatalogEntry | None:
        matches = self._by_code.get(compact_code(code), ())
        return matches[0] if len(matches) == 1 else None

    def find_all(self, code: str) -> tuple[CatalogEntry, ...]:
        return self._by_code.get(compact_code(code), ())

    def description(self, fraction: str, nico: str | None = None) -> str | None:
        target = f"{fraction}{nico}" if nico else fraction
        entry = self.get(target)
        return entry.description if entry else None

    def validate_result(self, fraction: str, nico: str | None) -> None:
        fraction_matches = tuple(
            entry for entry in self.find_all(fraction) if entry.kind == "fraction"
        )
        if len(fraction_matches) > 1:
            raise ValueError(f"Fraction {fraction} is ambiguous in the source catalog")
        fraction_entry = fraction_matches[0] if fraction_matches else None
        if fraction_entry is None:
            raise ValueError(f"Fraction {fraction} is not present in the source catalog")
        if nico is not None:
            nico_matches = tuple(
                entry for entry in self.find_all(f"{fraction}{nico}") if entry.kind == "nico"
            )
            if len(nico_matches) > 1:
                raise ValueError(f"NICO {fraction}-{nico} is ambiguous in the source catalog")
            nico_entry = nico_matches[0] if nico_matches else None
            if nico_entry is None:
                raise ValueError(f"NICO {fraction}-{nico} is not present in the source catalog")

