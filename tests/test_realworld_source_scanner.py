"""Regression coverage for import-backed crypto detection in real-world source shapes."""

from dataclasses import asdict
from pathlib import Path

from api.services.risk_engine import score_findings
from scanner import multilang_engine, python_engine


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_python_import_aliases_and_common_crypto_libraries(tmp_path: Path):
    path = _write(
        tmp_path,
        "crypto_usage.py",
        """
import hashlib as digest
import hmac
from cryptography.hazmat.primitives import hashes, algorithms
from cryptography.hazmat.primitives.asymmetric import ec, dsa
from Crypto.Cipher import DES3
from Crypto.Hash import MD5, SHA256

digest.new("sha1", b"payload")
digest.new("sha224", b"payload")
hmac.new(b"key", b"payload", digestmod="md5")
hashes.MD5()
algorithms.ARC4(b"key")
algorithms.TripleDES(b"123456789012345678901234")
ec.generate_private_key(ec.SECP256R1())
dsa.generate_private_key(key_size=2048)
DES3.new(b"123456789012345678901234", DES3.MODE_CBC, iv=b"12345678")
MD5.new(b"payload")
SHA256.new(b"payload")
""",
    )

    findings = python_engine.scan_file(path)
    assert {finding.algorithm for finding in findings} == {"SHA-1", "SHA-224", "SHA-256", "MD5", "RC4", "3DES", "ECC", "DSA"}
    assert all(finding.confidence == "high" for finding in findings)
    assert next(finding for finding in findings if finding.algorithm == "DSA").key_size == 2048


def test_python_does_not_report_unimported_lookalikes(tmp_path: Path):
    path = _write(
        tmp_path,
        "lookalike.py",
        """
class hashlib:
    @staticmethod
    def md5(value):
        return value

class AES:
    @staticmethod
    def new(value):
        return value

hashlib.md5(b"not a crypto library")
AES.new(b"not a crypto library")
""",
    )

    assert python_engine.scan_file(path) == []


def test_directory_named_target_is_not_treated_as_an_excluded_build_artifact(tmp_path: Path):
    root = tmp_path / "target"
    root.mkdir()
    _write(root, "legacy.py", "import hashlib\nhashlib.md5(b'x')\n")

    findings = python_engine.scan_directory(root)

    assert [finding.algorithm for finding in findings] == ["MD5"]


def test_javascript_and_typescript_import_forms_and_decoy_protection(tmp_path: Path):
    js_path = _write(
        tmp_path,
        "crypto_usage.js",
        """
const { createHash: makeHash, createCipheriv: makeCipher } = require("node:crypto");
import * as cryptoNamespace from "node:crypto";
import { createHash as importedHash } from "crypto";

makeHash("sha1");
makeCipher("des-ede3-cbc", Buffer.alloc(24), Buffer.alloc(8));
cryptoNamespace.createHash("sha256");
importedHash("sha512");
require("node:crypto").createHash("md5");
require("crypto").createCipher("des-cbc", Buffer.alloc(8));
cryptoNamespace.webcrypto.subtle.digest("SHA-1", new Uint8Array());
cryptoNamespace.webcrypto.subtle.generateKey({ name: "RSA-OAEP", modulusLength: 2048 }, true, ["encrypt"]);
""",
    )
    ts_path = _write(
        tmp_path,
        "crypto_usage.ts",
        """
import crypto from "node:crypto";
crypto.createCipheriv("aes-256-gcm", Buffer.alloc(32), Buffer.alloc(16));
""",
    )
    decoy_path = _write(
        tmp_path,
        "lookalike.js",
        """
const crypto = { createHash: () => "application helper" };
crypto.createHash("md5");
""",
    )

    rules = multilang_engine.load_rules(multilang_engine.RULES_DIR_DEFAULT)
    js_findings = multilang_engine.scan_file(js_path, rules)
    ts_findings = multilang_engine.scan_file(ts_path, rules)

    assert {finding.algorithm for finding in js_findings} == {"MD5", "SHA-1", "SHA-256", "SHA-512", "3DES", "DES", "RSA"}
    assert [finding.algorithm for finding in ts_findings] == ["AES"]
    assert all(finding.confidence == "high" for finding in [*js_findings, *ts_findings])
    assert multilang_engine.scan_file(decoy_path, rules) == []


def test_jsx_and_tsx_files_use_react_compatible_grammars(tmp_path: Path):
    jsx_path = _write(
        tmp_path,
        "widget.jsx",
        "import crypto from 'node:crypto'; export const Widget = () => <div>{crypto.createHash('sha256')}</div>;",
    )
    tsx_path = _write(
        tmp_path,
        "widget.tsx",
        "import crypto from 'node:crypto'; export const Widget = (): JSX.Element => <div>{crypto.createHash('sha512')}</div>;",
    )

    rules = multilang_engine.load_rules(multilang_engine.RULES_DIR_DEFAULT)
    jsx_findings = multilang_engine.scan_file(jsx_path, rules)
    tsx_findings = multilang_engine.scan_file(tsx_path, rules)

    assert [(finding.algorithm, finding.language, finding.confidence) for finding in jsx_findings] == [
        ("SHA-256", "javascript", "high")
    ]
    assert [(finding.algorithm, finding.language, finding.confidence) for finding in tsx_findings] == [
        ("SHA-512", "typescript", "high")
    ]


def test_node_module_extensions_and_webcrypto_calls_are_detected(tmp_path: Path):
    cjs_path = _write(
        tmp_path,
        "legacy.cjs",
        "const { webcrypto, createHmac } = require('node:crypto');\n"
        "webcrypto.subtle.digest('SHA-1', new Uint8Array());\n"
        "createHmac('sha256', 'key');\n",
    )
    mts_path = _write(
        tmp_path,
        "modern.mts",
        "import { createHash as digest } from 'node:crypto'; digest('sha512');",
    )
    dynamic_path = _write(
        tmp_path,
        "dynamic.mjs",
        "const crypto = await import('node:crypto'); crypto.createHash('sha224');",
    )
    browser_path = _write(
        tmp_path,
        "browser.js",
        "window.crypto.subtle.digest('SHA-1', new Uint8Array());\n"
        "globalThis.crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt']);\n"
        "const crypto = { subtle: { digest: () => undefined } }; crypto.subtle.digest('SHA-1', new Uint8Array());\n",
    )

    rules = multilang_engine.load_rules(multilang_engine.RULES_DIR_DEFAULT)
    cjs_findings = multilang_engine.scan_file(cjs_path, rules)
    mts_findings = multilang_engine.scan_file(mts_path, rules)
    dynamic_findings = multilang_engine.scan_file(dynamic_path, rules)
    browser_findings = multilang_engine.scan_file(browser_path, rules)

    assert {(finding.algorithm, finding.primitive) for finding in cjs_findings} == {
        ("SHA-1", "hash"),
        ("SHA-256", "mac"),
    }
    assert [(finding.algorithm, finding.language) for finding in mts_findings] == [
        ("SHA-512", "typescript")
    ]
    assert [(finding.algorithm, finding.confidence) for finding in dynamic_findings] == [
        ("SHA-224", "high")
    ]
    assert {(finding.algorithm, finding.confidence) for finding in browser_findings} == {
        ("SHA-1", "high"),
        ("AES", "high"),
    }


def test_java_standard_and_static_imports_are_high_confidence(tmp_path: Path):
    path = _write(
        tmp_path,
        "CryptoUsage.java",
        """
import java.security.MessageDigest;
import javax.crypto.Cipher;
import static java.security.MessageDigest.getInstance;

class CryptoUsage {
    void scan() throws Exception {
        MessageDigest.getInstance("SHA-256");
        getInstance("MD5");
        Cipher.getInstance("DESede/CBC/PKCS5Padding");
        java.security.MessageDigest.getInstance("SHA-1");
    }
}
""",
    )

    rules = multilang_engine.load_rules(multilang_engine.RULES_DIR_DEFAULT)
    findings = multilang_engine.scan_file(path, rules)
    assert {finding.algorithm for finding in findings} == {"MD5", "SHA-1", "SHA-256", "3DES"}
    assert all(finding.confidence == "high" for finding in findings)


def test_verified_mixed_language_findings_receive_deterministic_risk_tiers(tmp_path: Path):
    source_dir = tmp_path / "repository"
    source_dir.mkdir()
    _write(source_dir, "legacy.py", "import hashlib\nhashlib.md5(b'payload')\n")
    _write(
        source_dir,
        "CryptoUsage.java",
        "import javax.crypto.Cipher; class CryptoUsage { void run() throws Exception { Cipher.getInstance(\"DESede\"); } }",
    )
    _write(source_dir, "crypto.js", "const crypto = require('crypto'); crypto.createHash('sha256');")

    rules = multilang_engine.load_rules(multilang_engine.RULES_DIR_DEFAULT)
    findings = [
        *python_engine.scan_directory(source_dir),
        *multilang_engine.scan_directory(source_dir, rules),
    ]
    scored = score_findings([asdict(finding) for finding in findings])
    tiers = {finding["algorithm"]: finding["risk_tier"] for finding in scored}

    assert {finding["algorithm"] for finding in scored} == {"MD5", "3DES", "SHA-256"}
    assert tiers == {"MD5": "CRITICAL", "3DES": "HIGH", "SHA-256": "LOW"}
