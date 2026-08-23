"""
Unit tests for build_prompt, get_remediation_text, and LLM fallback behavior.
"""

from unittest.mock import MagicMock, patch
import pytest
from remediation import build_prompt, get_remediation_text


def test_build_prompt():
    """Test build_prompt generates expected prompt formatting and constraints."""
    prompt = build_prompt("MD5", "auth/hash.py", 42, "SHA-256 or BLAKE2")
    assert "MD5" in prompt
    assert "auth/hash.py" in prompt
    assert "42" in prompt
    assert "SHA-256 or BLAKE2" in prompt
    assert "1-2 sentences" in prompt
    assert "senior engineer's PR comment" in prompt
    assert "Do not suggest any fix other than the one given" in prompt


def test_get_remediation_text_success(monkeypatch):
    """Test get_remediation_text returns source 'llm' when LLM call succeeds."""
    monkeypatch.setenv("GOOGLE_API_KEY", "valid_mock_key")

    mock_response = MagicMock()
    mock_response.text = "MD5 is cryptographically broken for hashing. Recommended fix: SHA-256 or BLAKE2."

    with patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_model_instance

        res = get_remediation_text("MD5", "src/auth.py", 10)
        assert res["source"] == "llm"
        assert res["suggestion"] == mock_response.text


def test_get_remediation_text_fallback_on_invalid_key(monkeypatch):
    """
    Test that with the LLM API key deliberately invalidated/broken,
    get_remediation_text catches the exception and returns fallback with source 'table'.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "INVALID_API_KEY_12345")

    with patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.side_effect = Exception("400 API key not valid.")
        mock_model_cls.return_value = mock_model_instance

        res = get_remediation_text("MD5", "src/auth.py", 10)
        assert res["source"] == "table"
        assert "MD5 detected" in res["suggestion"]
        assert "SHA-256 or BLAKE2" in res["suggestion"]


def test_get_remediation_text_fallback_on_missing_key(monkeypatch):
    """
    Test fallback behavior when GOOGLE_API_KEY environment variable is absent.
    """
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    res = get_remediation_text("DES", "legacy/cipher.py", 88)
    assert res["source"] == "table"
    assert "DES detected" in res["suggestion"]
    assert "AES-256-GCM" in res["suggestion"]


def test_get_remediation_text_fallback_on_placeholder_key(monkeypatch):
    """
    Test fallback behavior when GOOGLE_API_KEY is set to default placeholder.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "your_key_here")

    res = get_remediation_text("SHA1", "crypto/hash.py", 15)
    assert res["source"] == "table"
    assert "SHA1 detected" in res["suggestion"]
    assert "SHA-256" in res["suggestion"]
