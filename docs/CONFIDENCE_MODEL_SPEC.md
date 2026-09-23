# ECDAT Unified Confidence Scoring Model Specification

## 1. Overview

This document specifies the rule-based, deterministic confidence scoring system for cryptographic asset discovery in ECDAT.
All detection engines (Python AST engine, tree-sitter multi-language engine, dependency engine, binary engine, and container engine) emit standardized evidence signals that are mapped to a numeric score $[0.00, 1.00]$ and a confidence band (`VERIFIED`, `PROBABLE`, `UNVERIFIED`).

## 2. Confidence Bands & Thresholds

| Band | Threshold | Description |
|---|---|---|
| `VERIFIED` | $\ge 0.85$ | Unambiguous call site with traced explicit import/binding and verified algorithm argument. |
| `PROBABLE` | $0.60 \le \text{score} < 0.85$ | Strong call site match or verified rule binding with minor ambiguity. |
| `UNVERIFIED` | $< 0.60$ | Heuristic match, unresolved dynamic argument, or inventory-level evidence. |

Band thresholds are inclusive at the lower bound.

## 3. Signal Vocabulary & Weights

| Signal | Weight | Description |
|---|---|---|
| `import_resolved` | $+0.35$ | Explicit import/require binding verified to the expected crypto library module. |
| `alias_traced` | $+0.15$ | Import alias or renamed identifier traced through AST/scope resolution. |
| `call_site_matched` | $+0.20$ | Cryptographic invocation matches a recognized API function/method signature. |
| `literal_algorithm_arg` | $+0.15$ | Algorithm identifier passed as a compile-time/static string constant. |
| `key_size_extracted` | $+0.05$ | Explicit key size or curve parameter extracted from call arguments. |
| `rule_yaml_matched` | $+0.10$ | Call matches an external YAML rule pattern. |
| `expected_module_confirmed` | $+0.20$ | Callee receiver confirmed to match the rule's expected namespace/module. |
| `dynamic_algorithm_arg` | $-0.20$ | Algorithm argument is a variable, expression, or dynamic lookup. |
| `import_unresolved` | $-0.40$ | Callee name matches crypto pattern but no supporting import was found. |
| `path_looks_like_test` | $-0.10$ | Source path indicates test, fixture, or mock code. |
| `path_looks_like_vendor` | $-0.10$ | Source path indicates vendored/third-party package code. |

## 4. Scoring Algorithm

1. Given a set of emitted signals $S$:
   $$\text{raw\_score} = \sum_{s \in S} \text{SIGNAL\_WEIGHTS}[s]$$
2. Score is clamped to the range $[0.00, 1.00]$ and rounded to 2 decimal places:
   $$\text{score} = \text{round}(\max(0.00, \min(1.00, \text{raw\_score})), 2)$$
3. Band is assigned based on threshold comparison against `BAND_THRESHOLDS`.

## 5. Legacy Compatibility

For backward compatibility with existing CBOM consumers, CLI integrations, and database records:
- Legacy `findings.confidence` TEXT column is populated as a derived value:
  - `VERIFIED` $\rightarrow$ `"high"`
  - `PROBABLE` $\rightarrow$ `"unverified"`
  - `UNVERIFIED` $\rightarrow$ `"unverified"`
- `confidence_score` (`NUMERIC(3,2)`), `confidence_band` (`TEXT`), and `confidence_signals` (`JSONB`) provide structured auditable evidence.

## 6. Model Versioning Policy

- Current version: `conf-1.0.0`
- Any change to signal weights, band thresholds, or vocabulary requires bumping `CONFIDENCE_MODEL_VERSION`.
- Past findings retain their original `confidence_model_version` tag for auditability.
