"""Format profiles for strict detection of known layouts versus unknown layouts."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata
import re

from backend.app.domain.document import DocumentLayout


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^\w]+", " ", without_marks, flags=re.UNICODE).strip()


@dataclass(frozen=True)
class FormatProfile:
    name: str
    required_signals: tuple[str, ...]
    weighted_signals: dict[str, float]
    negative_signals: tuple[str, ...] = ()
    min_confidence: float = 0.85

    def evaluate(self, text_corpus: str) -> tuple[float, tuple[str, ...]]:
        matched: list[str] = []
        compact_corpus = text_corpus.replace(" ", "")
        for negative in self.negative_signals:
            if negative in text_corpus or negative.replace(" ", "") in compact_corpus:
                return 0.0, ()

        for req in self.required_signals:
            if req not in text_corpus and req.replace(" ", "") not in compact_corpus:
                return 0.0, ()
            matched.append(f"required:{req}")

        score = 0.50  # Base score for fulfilling all required signals
        for sig, weight in self.weighted_signals.items():
            if sig in text_corpus or sig.replace(" ", "") in compact_corpus:
                score += weight
                matched.append(f"weighted:{sig}")

        final_score = min(1.0, round(score, 2))
        return final_score, tuple(matched)


KNOWN_PROFILES: tuple[FormatProfile, ...] = (
    FormatProfile(
        name="ARCELORMITTAL_CALVERT",
        required_signals=("arcelormittal calvert", "mill certificate"),
        weighted_signals={"chemical composition of the coil": 0.20, "steel grade customer specification": 0.20,
                          "tensile test": 0.10},
    ),
    FormatProfile(
        name="MOLINO_1_BX_POSCO",
        required_signals=("bx steel posco",),
        weighted_signals={
            "bta blz112": 0.20,
            "cold rolled steel strip": 0.15,
            "e02511200001": 0.15,
            "astm a1008": 0.10,
        },
        negative_signals=("bengang", "china steel", "secc"),
        min_confidence=0.85,
    ),
    FormatProfile(
        name="MOLINO_2_BENGANG",
        required_signals=("bengang",),
        weighted_signals={
            "e02604270139": 0.20,
            "sae1010mod": 0.20,
            "cold rolled steel strip": 0.15,
            "bta blz043": 0.15,
        },
        negative_signals=("bx steel posco", "china steel", "secc"),
        min_confidence=0.85,
    ),
    FormatProfile(
        name="MOLINO_3_CHINA_STEEL",
        required_signals=("china steel corporation",),
        weighted_signals={
            "sae 1035": 0.20,
            "150612h0039": 0.20,
            "hanwa": 0.15,
            "mill edge": 0.10,
        },
        negative_signals=("bengang", "posco", "secc"),
        min_confidence=0.85,
    ),
    FormatProfile(
        name="MOLINO_4_POSCO_EG",
        required_signals=("posco", "secc"),
        weighted_signals={
            "eg coil": 0.20,
            "240816 fz01ps": 0.20,
            "cr free phosphate": 0.15,
            "ladle": 0.10,
        },
        negative_signals=("bengang", "china steel", "bta blz112"),
        min_confidence=0.85,
    ),
)


def evaluate_format_profiles(
    document: DocumentLayout,
    profiles: tuple[FormatProfile, ...] = KNOWN_PROFILES,
    min_confidence: float = 0.85,
) -> tuple[str | None, float, tuple[str, ...]]:
    """Determine whether the document matches a known mill format with high confidence."""
    text_corpus = _normalize_text(document.text)
    best_name: str | None = None
    best_score: float = 0.0
    best_signals: tuple[str, ...] = ()

    for profile in profiles:
        score, signals = profile.evaluate(text_corpus)
        threshold = max(min_confidence, profile.min_confidence)
        if score >= threshold and score > best_score:
            best_score = score
            best_name = profile.name
            best_signals = signals

    return best_name, best_score, best_signals
