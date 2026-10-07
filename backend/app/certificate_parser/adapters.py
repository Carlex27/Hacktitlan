"""Adapter contracts for known layouts without coupling the generic detector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from backend.app.domain.document import DocumentLayout


@dataclass(frozen=True)
class AdapterMatch:
    adapter_name: str
    confidence: float
    reasons: tuple[str, ...] = ()


class CertificateAdapter(Protocol):
    name: str

    def match(self, document: DocumentLayout) -> AdapterMatch: ...

    def extract(self, document: DocumentLayout) -> dict[str, Any]: ...


class AdapterRegistry:
    def __init__(self, adapters: tuple[CertificateAdapter, ...] = ()) -> None:
        self._adapters = list(adapters)

    def register(self, adapter: CertificateAdapter) -> None:
        if any(item.name == adapter.name for item in self._adapters):
            raise ValueError(f"Adapter already registered: {adapter.name}")
        self._adapters.append(adapter)

    def best_match(self, document: DocumentLayout, minimum_confidence: float = 0.75) -> CertificateAdapter | None:
        ranked = sorted(
            ((adapter.match(document).confidence, adapter) for adapter in self._adapters),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked or ranked[0][0] < minimum_confidence:
            return None
        return ranked[0][1]

