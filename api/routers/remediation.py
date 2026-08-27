"""
Remediation Service Module for ECDAT.

Provides multi-provider LLM rephrasing (Gemini, OpenAI, Grok/xAI, Groq/Llama, NVIDIA Build/Llama, Ollama)
backed by deterministic rule-based cryptographic remediation tables and automatic provider auto-detection.
"""

from __future__ import annotations

import os
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from sqlalchemy.orm import Session

from api.core.config import settings
from api.core.security import get_api_key
from api.database import get_session
from api.models import RemediationOut, RemediationRequest
from db import crud
from remediation_table import get_criticality, get_remediation

router = APIRouter()


def build_prompt(algorithm: str, file: str, line: int, base_fix: str) -> str:
    """
    Generate a prompt asking the LLM to phrase the given fix as a 1-2 sentence
    senior-engineer PR comment, explicitly instructing it not to suggest any fix
    other than the one given.

    Args:
        algorithm: Canonical algorithm name (e.g. 'MD5').
        file: Source code file path.
        line: Line number in file.
        base_fix: Recommended fix string from rule-based table.

    Returns:
        Formatted prompt string.
    """
    return (
        f"This file '{file}' uses {algorithm} at line {line}. "
        f"The recommended fix is {base_fix}. "
        "Explain the risk and the fix in 1-2 sentences, like a senior engineer's PR comment. "
        "Do not suggest any fix other than the one given."
    )


def detect_provider(api_key: Optional[str] = None, requested_provider: Optional[str] = None) -> tuple[str, str | None]:
    """
    Detect the LLM provider and effective API key based on explicit parameter,
    key format/prefix heuristics, or environment variables.
    """
    if requested_provider:
        prov = requested_provider.lower().strip()
        if prov in {"gemini", "google"}:
            return "gemini", api_key or settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")
        elif prov in {"openai", "chatgpt"}:
            return "openai", api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        elif prov in {"grok", "xai"}:
            return "grok", api_key or settings.GROK_API_KEY or settings.XAI_API_KEY or os.getenv("GROK_API_KEY")
        elif prov in {"groq", "llama", "groq-llama"}:
            return "groq", api_key or settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        elif prov in {"nvidia", "nvidia-nim", "nvidia-llama"}:
            return "nvidia", api_key or settings.NVIDIA_BUILD_API_KEY or os.getenv("NVIDIA_BUILD_API_KEY")
        elif prov in {"ollama", "local"}:
            return "ollama", None

    # Key prefix heuristic
    if api_key:
        clean_key = api_key.strip()
        if clean_key.startswith("AIza"):
            return "gemini", clean_key
        elif clean_key.startswith("xai-"):
            return "grok", clean_key
        elif clean_key.startswith("gsk_"):
            return "groq", clean_key
        elif clean_key.startswith("nvapi-"):
            return "nvidia", clean_key
        elif clean_key.startswith("sk-") or clean_key.startswith("sk-proj-"):
            return "openai", clean_key

    # Environment fallback check in priority order
    google_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")
    if google_key and google_key != "your_key_here":
        return "gemini", google_key

    openai_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key != "your_key_here":
        return "openai", openai_key

    grok_key = settings.GROK_API_KEY or settings.XAI_API_KEY or os.getenv("GROK_API_KEY")
    if grok_key and grok_key != "your_key_here":
        return "grok", grok_key

    groq_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
    if groq_key and groq_key != "your_key_here":
        return "groq", groq_key

    nvidia_key = settings.NVIDIA_BUILD_API_KEY or os.getenv("NVIDIA_BUILD_API_KEY")
    if nvidia_key and nvidia_key != "your_key_here":
        return "nvidia", nvidia_key

    return "gemini", api_key


def _call_gemini(prompt: str, api_key: str, model_name: str = "gemini-1.5-flash") -> str:
    """Invoke Google Gemini API."""
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model_name, contents=prompt)
    if response and hasattr(response, "text") and response.text:
        return response.text.strip()
    raise ValueError("Empty response from Gemini")


def _call_openai_compatible(
    prompt: str,
    api_key: str | None,
    base_url: str,
    model_name: str,
    timeout: float = 6.0,
) -> str:
    """Invoke any OpenAI-compatible completions API (OpenAI, Grok, Groq, NVIDIA, Ollama)."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "You are a senior security engineer providing precise, 1-2 sentence cryptographic remediation advice.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 150,
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if choices and "message" in choices[0] and "content" in choices[0]["message"]:
            return choices[0]["message"]["content"].strip()
    raise ValueError("Empty or invalid response from OpenAI-compatible endpoint")


def get_remediation_text(
    algorithm: str,
    file: str = "unknown",
    line: int = 1,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """
    Fetch remediation recommendation text for a given finding.
    Supports Gemini, OpenAI, Grok, Groq (Llama), NVIDIA (Llama), and Ollama.
    Falls back reliably to rule-based table on any failure, rate limit, or timeout.
    """
    rem = get_remediation(algorithm)
    base_fix = rem["fix"]
    reason = rem["reason"]
    criticality = get_criticality(file)

    fallback: dict[str, Any] = {
        "suggestion": f"{algorithm} detected. Fix: {base_fix}. {reason}",
        "source": "table",
        "provider": "table",
        "model": "rule_based_table",
        "fallback_used": True,
        "severity": criticality,
    }

    effective_provider, effective_key = detect_provider(api_key, provider)

    # Remote LLM calls can disclose file paths and crypto usage to a third
    # party. They are disabled unless an administrator explicitly enables the
    # approved egress path. Prefer the deterministic local table for the
    # air-gapped/offline product mode.
    if effective_provider != "ollama" and not settings.ALLOW_REMOTE_REMEDIATION:
        return fallback

    if not effective_key and effective_provider != "ollama":
        return fallback

    if effective_key in {"your_key_here", "change_me_locally", ""}:
        return fallback

    prompt = build_prompt(algorithm, file, line, base_fix)
    timeout = getattr(settings, "LLM_TIMEOUT_SECONDS", 6.0)

    try:
        if effective_provider == "gemini":
            selected_model = model or getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
            text = _call_gemini(prompt, effective_key, selected_model)

            return {
                "suggestion": text,
                "source": "llm",
                "provider": "gemini",
                "model": selected_model,
                "fallback_used": False,
                "severity": criticality,
            }

        elif effective_provider == "openai":
            selected_model = model or settings.OPENAI_MODEL
            text = _call_openai_compatible(
                prompt,
                effective_key,
                settings.OPENAI_BASE_URL,
                selected_model,
                timeout,
            )
            return {
                "suggestion": text,
                "source": "llm",
                "provider": "openai",
                "model": selected_model,
                "fallback_used": False,
                "severity": criticality,
            }

        elif effective_provider == "grok":
            selected_model = model or settings.GROK_MODEL
            text = _call_openai_compatible(
                prompt,
                effective_key,
                settings.GROK_BASE_URL,
                selected_model,
                timeout,
            )
            return {
                "suggestion": text,
                "source": "llm",
                "provider": "grok",
                "model": selected_model,
                "fallback_used": False,
                "severity": criticality,
            }

        elif effective_provider == "groq":
            selected_model = model or settings.GROQ_MODEL
            text = _call_openai_compatible(
                prompt,
                effective_key,
                settings.GROQ_BASE_URL,
                selected_model,
                timeout,
            )
            return {
                "suggestion": text,
                "source": "llm",
                "provider": "groq",
                "model": selected_model,
                "fallback_used": False,
                "severity": criticality,
            }

        elif effective_provider == "nvidia":
            selected_model = model or settings.NVIDIA_MODEL
            text = _call_openai_compatible(
                prompt,
                effective_key,
                settings.NVIDIA_BASE_URL,
                selected_model,
                timeout,
            )
            return {
                "suggestion": text,
                "source": "llm",
                "provider": "nvidia",
                "model": selected_model,
                "fallback_used": False,
                "severity": criticality,
            }

        elif effective_provider == "ollama":
            selected_model = model or settings.OLLAMA_MODEL
            text = _call_openai_compatible(
                prompt,
                None,
                settings.OLLAMA_BASE_URL,
                selected_model,
                timeout,
            )
            return {
                "suggestion": text,
                "source": "llm",
                "provider": "ollama",
                "model": selected_model,
                "fallback_used": False,
                "severity": criticality,
            }

        return fallback

    except Exception:
        # Fall back gracefully on any network error, auth failure, timeout, or rate limit
        return fallback


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "supported_providers": ["gemini", "openai", "grok", "groq", "nvidia", "ollama"],
    }


@router.get("/{scan_id}/remediation/{finding_id}", response_model=RemediationOut)
async def get_remediation_for_finding(
    scan_id: int,
    finding_id: int,
    provider: Optional[str] = Query(None, description="Optional provider ('gemini', 'openai', 'grok', 'groq', 'nvidia', 'ollama')"),
    model: Optional[str] = Query(None, description="Optional model identifier override"),
    db: Session = Depends(get_session),
    _key: str = Depends(get_api_key),
):
    """
    Get remediation recommendation for a specific finding in its owning scan.
    A nonexistent finding or one belonging to another scan is not remediated
    through this route, preventing misleading fallback data and object-ID
    confusion across reports.
    """
    finding_row = crud.get_finding(db, finding_id)
    if finding_row is None or finding_row.scan_id != scan_id:
        raise HTTPException(status_code=404, detail="Finding not found in the requested scan")

    algorithm = finding_row.algorithm
    file_path = finding_row.file
    line_no = finding_row.line
    severity = finding_row.risk_tier or finding_row.criticality

    result = get_remediation_text(
        algorithm=algorithm,
        file=file_path,
        line=line_no,
        api_key=None,
        provider=provider,
        model=model,
    )
    result["finding_id"] = finding_id
    if severity and ("severity" not in result or not result["severity"]):
        result["severity"] = severity
    return result


@router.post("/remediation/generate", response_model=RemediationOut)
async def generate_remediation_direct(
    req: RemediationRequest,
    _key: str = Depends(get_api_key),
):
    """
    Ad-hoc direct endpoint to generate remediation from a server-configured
    provider or the deterministic local table. It never accepts provider
    credentials from an HTTP request.
    """
    result = get_remediation_text(
        algorithm=req.algorithm,
        file=req.file,
        line=req.line,
        api_key=None,
        provider=req.provider,
        model=req.model,
    )
    return result

