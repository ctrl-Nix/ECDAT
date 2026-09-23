"""
tests/test_confidence_scoring.py — Unit tests for unified confidence scoring.

Verifies deterministic calculation of confidence scores, bands, signals,
legacy compatibility values, and threshold checks across engines.
"""

import os
import pytest

from scanner.confidence import (
    BAND_THRESHOLDS,
    CONFIDENCE_BANDS,
    CONFIDENCE_MODEL_VERSION,
    ConfidenceBand,
    ConfidenceSignal,
    SIGNAL_WEIGHTS,
    band_for_score,
    calculate_confidence_score,
    legacy_confidence_for,
    meets_band_threshold,
)


def test_empty_signals():
    verdict = calculate_confidence_score([])
    assert verdict.score == 0.0
    assert verdict.band == ConfidenceBand.UNVERIFIED.value
    assert verdict.signals == []
    assert verdict.model_version == CONFIDENCE_MODEL_VERSION


def test_verified_signals():
    signals = [
        "import_resolved",
        "call_site_matched",
        "literal_algorithm_arg",
        "expected_module_confirmed",
    ]
    verdict = calculate_confidence_score(signals)
    # 0.35 + 0.20 + 0.15 + 0.20 = 0.90
    assert verdict.score == 0.90
    assert verdict.score >= 0.85
    assert verdict.band == "VERIFIED"
    assert verdict.signals == sorted(signals)


def test_probable_signals():
    # 0.35 (import_resolved) + 0.20 (call_site_matched) + 0.10 (rule_yaml_matched) = 0.65
    signals = ["import_resolved", "call_site_matched", "rule_yaml_matched"]
    verdict = calculate_confidence_score(signals)
    assert 0.60 <= verdict.score < 0.85
    assert verdict.band == "PROBABLE"


def test_unverified_negative_signals():
    signals = ["rule_yaml_matched", "dynamic_algorithm_arg", "import_unresolved"]
    verdict = calculate_confidence_score(signals)
    # 0.10 - 0.20 - 0.40 = -0.50 -> clamped to 0.00
    assert verdict.score == 0.00
    assert verdict.score < 0.60
    assert verdict.band == "UNVERIFIED"


def test_band_for_score_thresholds():
    assert band_for_score(0.849) == "PROBABLE"
    assert band_for_score(0.850) == "VERIFIED"
    assert band_for_score(1.00) == "VERIFIED"
    assert band_for_score(0.600) == "PROBABLE"
    assert band_for_score(0.599) == "UNVERIFIED"
    assert band_for_score(0.000) == "UNVERIFIED"


def test_meets_band_threshold():
    assert meets_band_threshold("PROBABLE", "VERIFIED") is False
    assert meets_band_threshold("VERIFIED", "PROBABLE") is True
    assert meets_band_threshold("VERIFIED", "VERIFIED") is True
    assert meets_band_threshold("PROBABLE", "PROBABLE") is True
    assert meets_band_threshold("UNVERIFIED", "PROBABLE") is False
    assert meets_band_threshold("UNVERIFIED", "UNVERIFIED") is True


def test_legacy_confidence_for():
    assert legacy_confidence_for("VERIFIED") == "high"
    assert legacy_confidence_for("PROBABLE") == "unverified"
    assert legacy_confidence_for("UNVERIFIED") == "unverified"


def test_unknown_signals_preservation_and_zero_weight():
    signals = ["custom_unknown_signal", "import_resolved"]
    verdict = calculate_confidence_score(signals)
    assert verdict.score == 0.35
    assert "custom_unknown_signal" in verdict.signals
    assert "import_resolved" in verdict.signals


def test_clamping_upper_bound():
    all_positive = [
        "import_resolved",
        "alias_traced",
        "call_site_matched",
        "literal_algorithm_arg",
        "key_size_extracted",
        "rule_yaml_matched",
        "expected_module_confirmed",
    ]
    verdict = calculate_confidence_score(all_positive)
    assert verdict.score == 1.00
    assert verdict.band == "VERIFIED"


def test_env_var_scan_min_confidence_band_override(monkeypatch):
    monkeypatch.setenv("SCAN_MIN_CONFIDENCE_BAND", "VERIFIED")
    from api.services.scan_runner import _passes_gate

    assert _passes_gate({"confidence_band": "VERIFIED"}) is True
    assert _passes_gate({"confidence_band": "PROBABLE"}) is False
    assert _passes_gate({"confidence_band": "UNVERIFIED"}) is False

    monkeypatch.setenv("SCAN_MIN_CONFIDENCE_BAND", "UNVERIFIED")
    assert _passes_gate({"confidence_band": "UNVERIFIED"}) is True
