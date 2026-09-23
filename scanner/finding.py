"""
Unified Finding schema -- shared by every detection engine (Python's
ast-based engine, the tree-sitter Java/JS engine, and any engine added
later). Every engine MUST produce this exact shape so the downstream
CBOM/risk stage never needs to know which engine or language a finding
came from.

Adding a new language later means: emit this dataclass from the new
engine. Nothing downstream changes.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class Finding:
    file: str
    line: int
    matched_call: str
    library: str
    algorithm: str
    primitive: str
    language: str
    weak_by_default: bool
    # "high"       = detection fully verified (import/require traced to the
    #                real module/class, or Python's alias resolution)
    # "unverified" = object name matched a rule, but the binding could not
    #                be traced back to the expected import/require
    confidence: str = "high"
    key_size: Optional[int] = None
    detection_method: str = "static_analysis"

    # ── CONF additions (one-time extension per contract §1.1, C-03) ─────────
    confidence_score: float = 0.0
    confidence_band: str = "UNVERIFIED"
    confidence_signals: list[str] = field(default_factory=list)
    confidence_model_version: str = "conf-1.0.0"

    def to_dict(self) -> dict:
        return asdict(self)