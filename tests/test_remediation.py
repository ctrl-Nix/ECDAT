"""
Unit tests for build_prompt, get_remediation_text, and LLM fallback behavior.
"""

from unittest.mock import MagicMock, patch
import pytest
from api.routers.remediation import build_prompt, get_remediation_text


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

    with patch("google.genai.Client") as mock_client_cls:
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client_instance

        res = get_remediation_text("MD5", "src/auth.py", 10)
        assert res["source"] == "llm"
        assert res["suggestion"] == mock_response.text


def test_get_remediation_text_fallback_on_invalid_key(monkeypatch):
    """
    Test that with the LLM API key deliberately invalidated/broken,
    get_remediation_text catches the exception and returns fallback with source 'table'.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "INVALID_API_KEY_12345")

    with patch("google.genai.Client") as mock_client_cls:
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = Exception("400 API key not valid.")
        mock_client_cls.return_value = mock_client_instance

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


def test_detect_provider():
    from api.routers.remediation import detect_provider

    assert detect_provider("AIzaSyB-12345")[0] == "gemini"
    assert detect_provider("sk-proj-12345")[0] == "openai"
    assert detect_provider("xai-12345")[0] == "grok"
    assert detect_provider("gsk_12345")[0] == "groq"
    assert detect_provider("nvapi-12345")[0] == "nvidia"
    assert detect_provider(requested_provider="ollama")[0] == "ollama"
    assert detect_provider(requested_provider="llama")[0] == "groq"


def test_get_remediation_openai_compatible(monkeypatch):
    """Test OpenAI / Grok / Groq / Llama execution via mocked HTTPX."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Use SHA-256 instead of MD5 for secure hashing."}}]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_resp):
        res = get_remediation_text("MD5", "src/auth.py", 10, api_key="sk-proj-testkey")
        assert res["source"] == "llm"
        assert res["provider"] == "openai"
        assert "SHA-256" in res["suggestion"]
        assert res["fallback_used"] is False


def test_get_remediation_groq_llama(monkeypatch):
    """Test Groq Llama provider with gsk_ key."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Replace DES with AES-256-GCM to prevent cryptanalytic attacks."}}]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_resp):
        res = get_remediation_text("DES", "src/crypto.py", 25, api_key="gsk_mock_groq_key")
        assert res["source"] == "llm"
        assert res["provider"] == "groq"
        assert "AES-256-GCM" in res["suggestion"]

