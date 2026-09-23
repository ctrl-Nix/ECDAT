"""SQLAlchemy ORM models for ECDAT's local scan and secure report lifecycle."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


SCAN_STATUSES = ("pending", "running", "completed", "failed")
RISK_TIERS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
CRITICALITIES = ("MEDIUM", "HIGH", "CRITICAL")
CONFIDENCES = ("low", "medium", "high")
CONFIDENCE_BANDS = ("VERIFIED", "PROBABLE", "UNVERIFIED")
ROLES = ("SECURITY_ADMIN", "AUDITOR", "DEVELOPER")
ARTIFACT_TYPES = ("SOURCE_FILE", "DEPENDENCY_MANIFEST", "CONFIG_FILE", "BINARY", "CONTAINER_LAYER")
PACKAGE_ECOSYSTEMS = ("pypi", "npm", "maven", "deb", "apk", "rpm")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(Text, index=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)



class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    organization_id: Mapped[str | None] = mapped_column(Text, index=True)
    external_id: Mapped[str | None] = mapped_column(Text)

    scans: Mapped[list["Scan"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", passive_deletes=True
    )


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int | None] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE")
    )
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(Text, default="pending")
    source_scan_id: Mapped[str | None] = mapped_column(Text)
    scan_context: Mapped[str | None] = mapped_column(Text)

    repository: Mapped["Repository"] = relationship(back_populates="scans")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan", passive_deletes=True
    )
    report: Mapped["Report | None"] = relationship(back_populates="scan", uselist=False)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int | None] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE")
    )
    file: Mapped[str] = mapped_column(Text, nullable=False)
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    key_size: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(Text, default="high")
    matched_call: Mapped[str | None] = mapped_column(Text)
    library: Mapped[str | None] = mapped_column(Text)
    primitive: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    weak_by_default: Mapped[bool | None] = mapped_column(Boolean)
    detection_method: Mapped[str | None] = mapped_column(Text)
    source_context: Mapped[str] = mapped_column(Text, default="SOURCE", nullable=False)
    risk_tier: Mapped[str | None] = mapped_column(Text)
    risk_reason: Mapped[str | None] = mapped_column(Text)
    criticality: Mapped[str] = mapped_column(Text, default="MEDIUM")
    confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2))
    confidence_band: Mapped[str | None] = mapped_column(Text)
    confidence_signals: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql")
    )
    artifact_type: Mapped[str] = mapped_column(Text, default="SOURCE_FILE", server_default="SOURCE_FILE", nullable=False)
    artifact_ref: Mapped[str | None] = mapped_column(Text)
    package_ecosystem: Mapped[str | None] = mapped_column(Text)
    package_name: Mapped[str | None] = mapped_column(Text)
    package_version: Mapped[str | None] = mapped_column(Text)
    image_digest: Mapped[str | None] = mapped_column(Text)
    layer_digest: Mapped[str | None] = mapped_column(Text)

    scan: Mapped["Scan"] = relationship(back_populates="findings")
    risk_assessment: Mapped["RiskAssessment | None"] = relationship(
        back_populates="finding", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        Index("idx_findings_scan_id", "scan_id"),
        Index("idx_findings_severity", "risk_tier"),
        Index("idx_findings_source_context", "source_context"),
        Index("idx_findings_confidence_band", "confidence_band"),
        Index("idx_findings_artifact_type", "artifact_type"),
        Index(
            "idx_findings_package",
            "package_ecosystem",
            "package_name",
            postgresql_where=text("package_name IS NOT NULL"),
        ),
    )


class RiskAssessment(Base):
    """Versioned deterministic PQC/classical assessment for a discovered asset."""

    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    risk_model_version: Mapped[str] = mapped_column(Text, nullable=False)
    classical_broken: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quantum_vulnerable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hndl_exposure: Mapped[str] = mapped_column(Text, default="UNKNOWN", nullable=False)
    recommended_replacement: Mapped[str | None] = mapped_column(Text)
    recommendation_type: Mapped[str | None] = mapped_column(Text)
    migration_effort_days: Mapped[int | None] = mapped_column(Integer)
    data_shelf_life_years: Mapped[float | None] = mapped_column()
    quantum_threat_horizon_years: Mapped[float | None] = mapped_column()
    assumption_source: Mapped[str | None] = mapped_column(Text)
    assessed_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    finding: Mapped["Finding"] = relationship(back_populates="risk_assessment")


class Report(Base):
    """Custody record for one signed report accepted from an enrolled agent."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    organization_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    repository_id: Mapped[str] = mapped_column(Text, nullable=False)
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_digest: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(Text, default="CONFIDENTIAL", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime)

    scan: Mapped["Scan"] = relationship(back_populates="report")
