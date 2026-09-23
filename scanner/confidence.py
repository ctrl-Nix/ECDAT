"""
scanner/confidence.py — Unified confidence scoring across every ECDAT engine.

Signals emitted by a detection engine are mapped, deterministically and
without any learned component, to a numeric score in [0.0, 1.0] and a
band in {VERIFIED, PROBABLE, UNVERIFIED}. Every engine feeds the same
scorer so a Python AST finding and a tree-sitter Java finding at the
same score mean the same thing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ConfidenceBand(str, Enum):
    VERIFIED = "VERIFIED"
    PROBABLE = "PROBABLE"
    UNVERIFIED = "UNVERIFIED"


CONFIDENCE_BANDS: tuple[str, ...] = tuple(band.value for band in ConfidenceBand)

# Band thresholds — the low bound is inclusive.
BAND_THRESHOLDS: dict[str, float] = {
    ConfidenceBand.VERIFIED.value: 0.85,
    ConfidenceBand.PROBABLE.value: 0.60,
    ConfidenceBand.UNVERIFIED.value: 0.00,
}

_BAND_RANKS: dict[str, int] = {
    ConfidenceBand.UNVERIFIED.value: 0,
    ConfidenceBand.PROBABLE.value: 1,
    ConfidenceBand.VERIFIED.value: 2,
}


class ConfidenceSignal(str, Enum):
    IMPORT_RESOLVED = "import_resolved"
    ALIAS_TRACED = "alias_traced"
    CALL_SITE_MATCHED = "call_site_matched"
    LITERAL_ALGORITHM_ARG = "literal_algorithm_arg"
    KEY_SIZE_EXTRACTED = "key_size_extracted"
    RULE_YAML_MATCHED = "rule_yaml_matched"
    EXPECTED_MODULE_CONFIRMED = "expected_module_confirmed"
    DYNAMIC_ALGORITHM_ARG = "dynamic_algorithm_arg"  # negative
    IMPORT_UNRESOLVED = "import_unresolved"  # negative
    PATH_LOOKS_LIKE_TEST = "path_looks_like_test"  # negative
    PATH_LOOKS_LIKE_VENDOR = "path_looks_like_vendor"  # negative


SIGNAL_WEIGHTS: dict[str, float] = {
    ConfidenceSignal.IMPORT_RESOLVED.value: 0.35,
    ConfidenceSignal.ALIAS_TRACED.value: 0.15,
    ConfidenceSignal.CALL_SITE_MATCHED.value: 0.20,
    ConfidenceSignal.LITERAL_ALGORITHM_ARG.value: 0.15,
    ConfidenceSignal.KEY_SIZE_EXTRACTED.value: 0.05,
    ConfidenceSignal.RULE_YAML_MATCHED.value: 0.10,
    ConfidenceSignal.EXPECTED_MODULE_CONFIRMED.value: 0.20,
    ConfidenceSignal.DYNAMIC_ALGORITHM_ARG.value: -0.20,
    ConfidenceSignal.IMPORT_UNRESOLVED.value: -0.40,
    ConfidenceSignal.PATH_LOOKS_LIKE_TEST.value: -0.10,
    ConfidenceSignal.PATH_LOOKS_LIKE_VENDOR.value: -0.10,
}

CONFIDENCE_MODEL_VERSION: str = "conf-1.0.0"


@dataclass(frozen=True)
class ConfidenceVerdict:
    score: float  # 0.00 – 1.00, rounded to 2 dp
    band: str  # one of CONFIDENCE_BANDS
    signals: list[str]  # deduplicated, sorted, subset of ConfidenceSignal values
    model_version: str  # CONFIDENCE_MODEL_VERSION


def band_for_score(score: float) -> str:
    """Return the band string for a numeric score in [0.0, 1.0]."""
    if score >= BAND_THRESHOLDS[ConfidenceBand.VERIFIED.value]:
        return ConfidenceBand.VERIFIED.value
    if score >= BAND_THRESHOLDS[ConfidenceBand.PROBABLE.value]:
        return ConfidenceBand.PROBABLE.value
    return ConfidenceBand.UNVERIFIED.value


def meets_band_threshold(band: str, minimum: str) -> bool:
    """Return True if `band` is at or above `minimum` in precedence."""
    band_rank = _BAND_RANKS.get(band, 0)
    min_rank = _BAND_RANKS.get(minimum, 0)
    return band_rank >= min_rank


def legacy_confidence_for(band: str) -> str:
    """Contract-mandated derived value for the legacy findings.confidence TEXT column."""
    if band == ConfidenceBand.VERIFIED.value:
        return "high"
    return "unverified"


def calculate_confidence_score(signals: Iterable[str]) -> ConfidenceVerdict:
    """Calculate deterministic confidence score and band from a set of signals."""
    deduped_signals = sorted(set(signals))
    raw_score = sum(SIGNAL_WEIGHTS.get(sig, 0.0) for sig in deduped_signals)
    clamped_score = round(max(0.0, min(1.0, raw_score)), 2)
    band = band_for_score(clamped_score)
    return ConfidenceVerdict(
        score=clamped_score,
        band=band,
        signals=deduped_signals,
        model_version=CONFIDENCE_MODEL_VERSION,
    )
