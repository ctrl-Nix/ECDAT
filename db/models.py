"""SQLAlchemy ORM models for ECDAT.

These mirror db/schema.sql exactly. schema.sql creates the tables in Postgres
on container init; these models are what the application reads/writes through.

The `findings` model stores every field the pipeline produces end-to-end:
  * all scanner evidence fields (scanner/finding.py: matched_call, library,
    primitive, language, weak_by_default, detection_method, ...)
  * the risk-engine interpretation (api/services/risk_engine.py: risk_tier,
    risk_reason, criticality, quantum_vulnerable, classical_broken,
    recommended_replacement, recommendation_type)
so nothing is dropped between scan and dashboard (see CODEBASE_AUDIT.md §3.2/§4).

Types are portable so the offline test-suite can spin the same models up on
SQLite (no Docker needed), while still emitting the right Postgres types on
Postgres.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Allowed enum-like values, kept next to the models so crud normalization and
# the CHECK constraints below share one definition. These MUST match the values
# produced in code (scanner/finding.py, api/services/risk_engine.py).
SCAN_STATUSES = ("pending", "running", "completed", "failed")
RISK_TIERS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
CRITICALITIES = ("MEDIUM", "HIGH", "CRITICAL")
RECOMMENDATION_TYPES = ("classical", "hybrid", "post-quantum")
# scanner emits "high" (verified) or "unverified"; seed/tests may use others.
CONFIDENCES = ("high", "unverified", "medium", "low")


class Base(DeclarativeBase):
    pass


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)

    scans: Mapped[list["Scan"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Repository id={self.id} name={self.name!r}>"


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int | None] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE")
    )
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(Text, default="pending")

    repository: Mapped["Repository"] = relationship(back_populates="scans")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="scans_status_valid",
        ),
        Index("idx_scans_repo_id", "repo_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Scan id={self.id} repo_id={self.repo_id} status={self.status!r}>"


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int | None] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE")
    )

    # --- Scanner evidence (scanner/finding.py) -----------------------------
    file: Mapped[str] = mapped_column(Text, nullable=False)
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    matched_call: Mapped[str | None] = mapped_column(Text)
    library: Mapped[str | None] = mapped_column(Text)
    primitive: Mapped[str | None] = mapped_column(Text)  # hash|cipher|signature|...
    language: Mapped[str | None] = mapped_column(Text)   # python|java|javascript
    weak_by_default: Mapped[bool | None] = mapped_column(Boolean)
    key_size: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(Text, default="high")
    detection_method: Mapped[str] = mapped_column(
        Text, default="static_analysis"
    )

    # --- Risk-engine interpretation (api/services/risk_engine.py) ----------
    risk_tier: Mapped[str | None] = mapped_column(Text)      # LOW/MEDIUM/HIGH/CRITICAL
    risk_reason: Mapped[str | None] = mapped_column(Text)
    criticality: Mapped[str] = mapped_column(Text, default="MEDIUM")
    quantum_vulnerable: Mapped[bool | None] = mapped_column(Boolean)
    classical_broken: Mapped[bool | None] = mapped_column(Boolean)
    recommended_replacement: Mapped[str | None] = mapped_column(Text)
    recommendation_type: Mapped[str | None] = mapped_column(Text)  # classical|hybrid|post-quantum

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    scan: Mapped["Scan"] = relationship(back_populates="findings")

    __table_args__ = (
        CheckConstraint(
            "risk_tier IS NULL OR "
            "risk_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="findings_risk_tier_valid",
        ),
        CheckConstraint(
            "criticality IN ('MEDIUM', 'HIGH', 'CRITICAL')",
            name="findings_criticality_valid",
        ),
        CheckConstraint(
            "recommendation_type IS NULL OR "
            "recommendation_type IN ('classical', 'hybrid', 'post-quantum')",
            name="findings_recommendation_type_valid",
        ),
        Index("idx_findings_scan_id", "scan_id"),
        Index("idx_findings_severity", "risk_tier"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<Finding id={self.id} scan_id={self.scan_id} "
            f"algorithm={self.algorithm!r} risk_tier={self.risk_tier!r}>"
        )
