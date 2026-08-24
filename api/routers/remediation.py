"""
Remediation Service Module for ECDAT.

Combines rule-based remediation lookups with LLM rephrasing capability,
providing robust fallback to static lookup tables.
"""

from fastapi import APIRouter, HTTPException

from remediation_table import get_remediation

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


def get_remediation_text(algorithm: str, file: str, line: int, api_key: str = None) -> dict:
    """
    Fetch remediation recommendation text for a given finding.
    Calls LLM if API key is valid, falling back to rule-based table on any failure.

    Args:
        algorithm: Canonical algorithm string.
        file: File path string.
        line: Line number integer.
        api_key: Optional explicit API key string.

    Returns:
        Dict with 'suggestion' and 'source' ('llm' or 'table') keys.
    """
    rem = get_remediation(algorithm)
    base_fix = rem["fix"]
    reason = rem["reason"]
    fallback = {
        "suggestion": f"{algorithm} detected. Fix: {base_fix}. {reason}",
        "source": "table",
    }

    try:
        import os

        import google.generativeai as genai

        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key or key == "your_key_here":
            raise ValueError("No valid API key provided")

        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = build_prompt(algorithm, file, line, base_fix)
        response = model.generate_content(prompt)

        if response and hasattr(response, "text") and response.text:
            return {"suggestion": response.text.strip(), "source": "llm"}
        raise ValueError("Empty or invalid response from LLM")
    except Exception:
        return fallback


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/{scan_id}/remediation/{finding_id}")
async def get_remediation_for_finding(scan_id: int, finding_id: int):
    fake_finding = {"algorithm": "MD5", "file": "auth.py", "line": 42}
    result = get_remediation_text(
        algorithm=fake_finding["algorithm"],
        file=fake_finding["file"],
        line=fake_finding["line"],
    )
    if not result:
        raise HTTPException(status_code=404, detail="No remediation available")
    return result
