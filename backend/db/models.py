"""SQLAlchemy ORM models for ECDAT.

These mirror backend/db/schema.sql exactly (the schema documented in
ARCHITECTURE.md). schema.sql is what creates the tables in Postgres on
container init; these models are what the application reads/writes through.

Types are portable so the offline test-suite can spin the same models up on
SQLite (no Docker needed), while still emitting the right Postgres types on
Postgres.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Allowed enum-like values, kept next to the models so crud normalization has
# one definition to reference. (No DB CHECK constraints -- ARCHITECTURE.md
# documents these as conventions, and crud normalizes to them.)
SCAN_STATUSES = ("pending", "running", "completed", "failed")
RISK_TIERS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
CRITICALITIES = ("MEDIUM", "HIGH", "CRITICAL")
CONFIDENCES = ("low", "medium", "high")


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
        DateTime, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(Text, default="pending")

    repository: Mapped["Repository"] = relationship(back_populates="scans")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Scan id={self.id} repo_id={self.repo_id} status={self.status!r}>"


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

    # Risk fields (see skills/cbom-quantum-risk/SKILL.md)
    risk_tier: Mapped[str | None] = mapped_column(Text)      # LOW/MEDIUM/HIGH/CRITICAL
    risk_reason: Mapped[str | None] = mapped_column(Text)
    criticality: Mapped[str] = mapped_column(Text, default="MEDIUM")

    scan: Mapped["Scan"] = relationship(back_populates="findings")

    __table_args__ = (
        Index("idx_findings_scan_id", "scan_id"),
        Index("idx_findings_severity", "risk_tier"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<Finding id={self.id} scan_id={self.scan_id} "
            f"algorithm={self.algorithm!r} risk_tier={self.risk_tier!r}>"
        )
