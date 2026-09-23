from __future__ import annotations

import datetime as dt
import json
import uuid
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from api.models import RiskSummary
from db.models import CRITICALITIES, RISK_TIERS

CBOM_VALIDATION_SCOPE: str = "ecdat-structural-invariants"
EXPECTED_BOM_FORMAT: str = "CycloneDX"
EXPECTED_SPEC_VERSION: str = "1.6"
CRYPTO_ASSET_TYPES: tuple[str, ...] = (
    "algorithm",
    "certificate",
    "protocol",
    "related-crypto-material",
)
UNSCORED_TIER: str = "UNSCORED"
RISK_TIER_PROPERTY: str = "ecdat:risk_tier"
CRITICALITY_PROPERTY: str = "ecdat:criticality"

CBOM_ISSUE_CODES: frozenset[str] = frozenset(
    {
        "DOCUMENT_NOT_OBJECT",
        "NOT_JSON_SERIALIZABLE",
        "FIELD_MISSING",
        "FIELD_WRONG_TYPE",
        "FIELD_INVALID_VALUE",
        "BOM_REF_DUPLICATE",
        "SUMMARY_TOTAL_MISMATCH",
        "SUMMARY_TIER_MISMATCH",
        "RISK_TIER_PROPERTY_MISSING",
        "RISK_TIER_PROPERTY_INVALID",
        "CRITICALITY_PROPERTY_INVALID",
    }
)


class CbomIssue(BaseModel):
    code: str
    path: str
    message: str


class CbomValidationResult(BaseModel):
    valid: bool
    scope: str = CBOM_VALIDATION_SCOPE
    issues: list[CbomIssue] = Field(default_factory=list)


_EXT = ConfigDict(extra="allow")


class _Property(BaseModel):
    model_config = _EXT
    name: str = Field(min_length=1)
    value: str


class _Occurrence(BaseModel):
    model_config = _EXT
    location: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=0, strict=True)


class _Evidence(BaseModel):
    model_config = _EXT
    occurrences: list[_Occurrence] = Field(min_length=1)


class _CryptoProperties(BaseModel):
    model_config = _EXT
    assetType: Literal["algorithm", "certificate", "protocol", "related-crypto-material"]
    algorithmProperties: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _algorithm_requires_properties(self) -> "_CryptoProperties":
        if self.assetType == "algorithm" and self.algorithmProperties is None:
            raise ValueError("algorithm assetType requires algorithmProperties")
        return self


class _Component(BaseModel):
    model_config = _EXT
    type: Literal["cryptographic-asset"]
    bom_ref: str = Field(alias="bom-ref", min_length=1)
    name: str = Field(min_length=1)
    cryptoProperties: _CryptoProperties
    evidence: _Evidence
    properties: list[_Property]


class _MetadataComponent(BaseModel):
    model_config = _EXT
    type: str = Field(min_length=1)
    name: str = Field(min_length=1)


class _Metadata(BaseModel):
    model_config = _EXT
    timestamp: str
    tools: list[Any] | dict[str, Any]
    component: _MetadataComponent | None = None

    @field_validator("timestamp")
    @classmethod
    def _iso8601(cls, v: str) -> str:
        dt.datetime.fromisoformat(v)
        return v


class _Document(BaseModel):
    model_config = _EXT
    bomFormat: Literal["CycloneDX"]
    specVersion: Literal["1.6"]
    serialNumber: str
    version: int = Field(ge=1, strict=True)
    metadata: _Metadata
    components: list[_Component]
    externalReferences: list[Any] | None = None
    x_ecdat_risk_summary: RiskSummary | None = Field(default=None, alias="x-ecdat-risk-summary")
    x_ecdat_report_provenance: dict[str, Any] | None = Field(
        default=None, alias="x-ecdat-report-provenance"
    )

    @field_validator("serialNumber")
    @classmethod
    def _urn_uuid(cls, v: str) -> str:
        if not v.startswith("urn:uuid:"):
            raise ValueError("serialNumber must begin with urn:uuid:")
        tail = v[len("urn:uuid:"):]
        try:
            parsed = uuid.UUID(tail)
        except (ValueError, AttributeError):
            raise ValueError("serialNumber must contain a valid UUID")
        if str(parsed) != tail:
            raise ValueError("serialNumber UUID must be canonical lower-case")
        return v


def _path(loc: tuple[Any, ...]) -> str:
    if not loc:
        return ""
    return "/" + "/".join(str(p) for p in loc)


def _classify(err_type: str) -> str:
    if err_type == "missing":
        return "FIELD_MISSING"
    if err_type.endswith("_type") or err_type.endswith("_parsing") or err_type == "model_type":
        return "FIELD_WRONG_TYPE"
    return "FIELD_INVALID_VALUE"


def _prop(component: _Component, name: str) -> list[str]:
    return [p.value for p in component.properties if p.name == name]


def _finish(issues: list[CbomIssue]) -> CbomValidationResult:
    sorted_issues = sorted(issues, key=lambda x: (x.path, x.code, x.message))
    return CbomValidationResult(
        valid=len(sorted_issues) == 0,
        scope=CBOM_VALIDATION_SCOPE,
        issues=sorted_issues,
    )


def validate_cbom(cbom: dict[str, Any]) -> CbomValidationResult:
    if not isinstance(cbom, dict):
        return _finish(
            [
                CbomIssue(
                    code="DOCUMENT_NOT_OBJECT",
                    path="",
                    message="Document must be a JSON object.",
                )
            ]
        )

    issues: list[CbomIssue] = []

    try:
        json.dumps(cbom, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        issues.append(
            CbomIssue(
                code="NOT_JSON_SERIALIZABLE",
                path="",
                message="Document is not JSON-serializable.",
            )
        )

    try:
        doc = _Document.model_validate(cbom)
    except ValidationError as exc:
        for err in exc.errors():
            code = _classify(err["type"])
            path = _path(err["loc"])
            msg = err["msg"]
            issues.append(CbomIssue(code=code, path=path, message=msg))
        return _finish(issues)
    except RecursionError:
        return _finish(issues)

    seen_refs: set[str] = set()
    reported_duplicate_refs: set[str] = set()
    allowed_tiers = set(RISK_TIERS) | {UNSCORED_TIER}
    allowed_criticalities = set(CRITICALITIES)
    tier_counts: dict[str, int] = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
        "UNSCORED": 0,
    }

    for i, component in enumerate(doc.components):
        ref = component.bom_ref
        if ref in seen_refs:
            if ref not in reported_duplicate_refs:
                issues.append(
                    CbomIssue(
                        code="BOM_REF_DUPLICATE",
                        path=f"/components/{i}/bom-ref",
                        message="bom-ref must be unique within the document.",
                    )
                )
                reported_duplicate_refs.add(ref)
        else:
            seen_refs.add(ref)

        tier_props = _prop(component, RISK_TIER_PROPERTY)
        if len(tier_props) != 1:
            issues.append(
                CbomIssue(
                    code="RISK_TIER_PROPERTY_MISSING",
                    path=f"/components/{i}/properties",
                    message=f"Component must have exactly one {RISK_TIER_PROPERTY} property.",
                )
            )
        else:
            tier_val = tier_props[0]
            if tier_val not in allowed_tiers:
                issues.append(
                    CbomIssue(
                        code="RISK_TIER_PROPERTY_INVALID",
                        path=f"/components/{i}/properties",
                        message=f"Property {RISK_TIER_PROPERTY} has invalid value.",
                    )
                )
            else:
                if tier_val in tier_counts:
                    tier_counts[tier_val] += 1

        crit_props = _prop(component, CRITICALITY_PROPERTY)
        for crit_val in crit_props:
            if crit_val not in allowed_criticalities:
                issues.append(
                    CbomIssue(
                        code="CRITICALITY_PROPERTY_INVALID",
                        path=f"/components/{i}/properties",
                        message=f"Property {CRITICALITY_PROPERTY} has invalid value.",
                    )
                )

    if doc.x_ecdat_risk_summary is not None:
        summary = doc.x_ecdat_risk_summary
        if summary.total != len(doc.components):
            issues.append(
                CbomIssue(
                    code="SUMMARY_TOTAL_MISMATCH",
                    path="/x-ecdat-risk-summary/total",
                    message="Summary total does not equal the component count.",
                )
            )
        for tier in ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNSCORED"):
            summary_tier_count = getattr(summary, tier)
            comp_tier_count = tier_counts.get(tier, 0)
            if summary_tier_count != comp_tier_count:
                issues.append(
                    CbomIssue(
                        code="SUMMARY_TIER_MISMATCH",
                        path=f"/x-ecdat-risk-summary/{tier}",
                        message=f"Summary count for {tier} does not match component properties.",
                    )
                )

    return _finish(issues)
