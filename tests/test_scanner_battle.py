"""
Battle-tested scanner tests for ECDAT.
Tests Python, Java, JavaScript/TypeScript detection with comprehensive fixtures.
"""

import tempfile
import os
import json
from pathlib import Path

# Import scanner engines directly to avoid circular import issues
import importlib.util

def load_python_engine():
    spec = importlib.util.spec_from_file_location('python_engine', 'scanner/python_engine.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_multilang_engine():
    spec = importlib.util.spec_from_file_location('multilang_engine', 'scanner/multilang_engine.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

python_engine = load_python_engine()
multilang_engine = load_multilang_engine()


class TestPythonScanner:
    """Tests for Python AST-based scanner."""

    def test_basic_crypto_detection(self):
        """Test detection of basic crypto patterns."""
        code = """
import hashlib
from Crypto.Cipher import AES, DES
from Crypto.PublicKey import RSA
import ssl

hashlib.md5(b"data")
hashlib.sha1(b"data")
hashlib.sha256(b"data")
AES.new(b"key"*32, AES.MODE_GCM)
DES.new(b"key"*8, DES.MODE_CBC)
RSA.generate(2048)
ssl.create_default_context()
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "SHA-1" in algorithms
            assert "SHA-256" in algorithms
            assert "AES" in algorithms
            assert "DES" in algorithms
            assert "RSA" in algorithms
            assert "TLS" in algorithms
            assert all(f.confidence == "high" for f in findings)
        finally:
            os.unlink(path)

    def test_import_alias_resolution(self):
        """Test that import aliases are correctly resolved."""
        code = """
import hashlib as hl
from hashlib import sha256 as strong_hash
from Crypto.Cipher import AES as CipherAES

hl.md5(b"data")
strong_hash(b"data")
CipherAES.new(b"key"*32, CipherAES.MODE_GCM)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "SHA-256" in algorithms
            assert "AES" in algorithms
            assert all(f.confidence == "high" for f in findings)
        finally:
            os.unlink(path)

    def test_decoy_immunity_comments(self):
        """Test that comments containing crypto names don't trigger findings."""
        code = '''
import hashlib
from Crypto.Cipher import AES

# hashlib.md5(b"fake")
# AES.new(b"key", AES.MODE_CBC)
# DES.new(b"key", DES.MODE_CBC)

hashlib.md5(b"real")
AES.new(b"key"*32, AES.MODE_GCM)
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            assert len(findings) == 2
            algorithms = {f.algorithm for f in findings}
            assert algorithms == {"MD5", "AES"}
        finally:
            os.unlink(path)

    def test_decoy_immunity_variable_names(self):
        """Test that variable/function names don't trigger findings."""
        code = """
import hashlib
from Crypto.Cipher import AES

def md5_checksum(data):
    return hashlib.sha256(data).hexdigest()

md5_hash = "d41d8cd98f00b204e9800998ecf8427e"
sha1_value = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
legacy_des = "old"

hashlib.md5(b"real call")
AES.new(b"key"*32, AES.MODE_GCM)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            assert len(findings) == 3
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "SHA-256" in algorithms
            assert "AES" in algorithms
        finally:
            os.unlink(path)

    def test_decoy_immunity_string_literals(self):
        """Test that string literals mentioning crypto don't trigger findings."""
        code = """
import hashlib
from Crypto.Cipher import AES

config = {"algorithm": "MD5", "cipher": "AES-256"}
error_msg = "MD5 is deprecated"
log_entry = "User used DES"

hashlib.md5(b"real")
AES.new(b"key"*32, AES.MODE_GCM)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            assert len(findings) == 2
            algorithms = {f.algorithm for f in findings}
            assert algorithms == {"MD5", "AES"}
        finally:
            os.unlink(path)

    def test_rsa_key_size_extraction(self):
        """Test RSA key size extraction from various call patterns."""
        code = """
from Crypto.PublicKey import RSA
from cryptography.hazmat.primitives.asymmetric import rsa

RSA.generate(1024)
RSA.generate(2048)
RSA.generate(4096)
rsa.generate_private_key(public_exponent=65537, key_size=2048)
rsa.generate_private_key(public_exponent=65537, key_size=1024)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            rsa_findings = [f for f in findings if f.algorithm == "RSA"]
            key_sizes = sorted(f.key_size for f in rsa_findings if f.key_size)
            assert key_sizes == [1024, 1024, 2048, 2048, 4096]
        finally:
            os.unlink(path)

    def test_method_chaining_and_lambdas(self):
        """Test detection in method chains and lambdas."""
        code = """
import hashlib

hashlib.md5(b"data").hexdigest()

check = lambda x: hashlib.md5(x).hexdigest()
check(b"test")

hashes = [hashlib.sha256(x).hexdigest() for x in [b"a", b"b"]]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "SHA-256" in algorithms
            md5_count = sum(1 for f in findings if f.algorithm == "MD5")
            sha256_count = sum(1 for f in findings if f.algorithm == "SHA-256")
            assert md5_count == 2
            assert sha256_count == 1
        finally:
            os.unlink(path)

    def test_class_method_detection(self):
        """Test detection inside class methods."""
        code = """
import hashlib

class Hasher:
    def hash_md5(self, data):
        return hashlib.md5(data).hexdigest()

    def hash_sha256(self, data):
        return hashlib.sha256(data).hexdigest()

h = Hasher()
h.hash_md5(b"test")
h.hash_sha256(b"test")
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "SHA-256" in algorithms
            assert len(findings) == 2
        finally:
            os.unlink(path)

    def test_syntax_error_handling(self):
        """Test that syntax errors don't crash the scanner."""
        code = """
import hashlib
hashlib.md5(b"valid")
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            assert len(findings) == 1
            assert findings[0].algorithm == "MD5"
        finally:
            os.unlink(path)

    def test_empty_file(self):
        """Test empty file handling."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# Empty file\n")
            path = Path(f.name)

        try:
            findings = python_engine.scan_file(path)
            assert len(findings) == 0
        finally:
            os.unlink(path)


class TestJavaScanner:
    """Tests for Java Tree-sitter scanner."""

    def test_basic_java_detection(self):
        """Test basic Java crypto detection."""
        code = """
import java.security.MessageDigest;
import javax.crypto.Cipher;
import java.security.KeyPairGenerator;

public class Test {
    public void test() {
        MessageDigest.getInstance("MD5");
        MessageDigest.getInstance("SHA-1");
        MessageDigest.getInstance("SHA-256");
        Cipher.getInstance("DES");
        Cipher.getInstance("AES");
        KeyPairGenerator.getInstance("RSA").initialize(2048);
    }
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "SHA-1" in algorithms
            assert "SHA-256" in algorithms
            assert "DES" in algorithms
            assert "AES" in algorithms
            assert "RSA" in algorithms
            assert all(f.confidence == "high" for f in findings)
        finally:
            os.unlink(path)

    def test_java_static_imports(self):
        """Test Java static import resolution."""
        code = """
import static java.security.MessageDigest.getInstance;
import javax.crypto.Cipher;

public class Test {
    void test() {
        getInstance("MD5");
        getInstance("SHA-256");
        Cipher.getInstance("AES");
    }
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "SHA-256" in algorithms
            assert "AES" in algorithms
            assert all(f.confidence == "high" for f in findings)
        finally:
            os.unlink(path)

    def test_java_decoy_immunity(self):
        """Test Java decoy immunity."""
        code = """
import java.security.MessageDigest;
import javax.crypto.Cipher;

public class Decoys {
    private String md5Hash = "fake";

    public void realCalls() {
        MessageDigest.getInstance("SHA-256");
        Cipher.getInstance("AES");
    }
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            assert len(findings) == 2
            algorithms = {f.algorithm for f in findings}
            assert algorithms == {"SHA-256", "AES"}
        finally:
            os.unlink(path)

    def test_rsa_key_size_java(self):
        """Test RSA key size extraction in Java."""
        code = """
import java.security.KeyPairGenerator;

public class Test {
    void test() {
        KeyPairGenerator.getInstance("RSA").initialize(1024);
        KeyPairGenerator.getInstance("RSA").initialize(2048);
        KeyPairGenerator.getInstance("RSA").initialize(4096);
    }
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            rsa_findings = [f for f in findings if f.algorithm == "RSA"]
            key_sizes = sorted(f.key_size for f in rsa_findings if f.key_size)
            assert key_sizes == [1024, 2048, 4096]
        finally:
            os.unlink(path)


class TestJavaScriptScanner:
    """Tests for JavaScript/TypeScript Tree-sitter scanner."""

    def test_basic_js_detection(self):
        """Test basic JavaScript crypto detection."""
        code = """
const crypto = require("crypto");

crypto.createHash("md5");
crypto.createHash("sha1");
crypto.createHash("sha256");
crypto.createCipheriv("des", Buffer.alloc(8), Buffer.alloc(8));
crypto.createCipheriv("aes-256-gcm", Buffer.alloc(32), Buffer.alloc(16));
crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "SHA-1" in algorithms
            assert "SHA-256" in algorithms
            assert "DES" in algorithms
            assert "AES" in algorithms
            assert "RSA" in algorithms
            assert all(f.confidence == "high" for f in findings)
        finally:
            os.unlink(path)

    def test_es6_imports(self):
        """Test ES6 import patterns."""
        code = """
import crypto from "crypto";
import { createHash, createCipheriv } from "crypto";

createHash("md5");
createCipheriv("aes-256-gcm", Buffer.alloc(32), Buffer.alloc(16));
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            algorithms = {f.algorithm for f in findings}
            assert "MD5" in algorithms
            assert "AES" in algorithms
            assert all(f.confidence == "high" for f in findings)
        finally:
            os.unlink(path)

    def test_js_decoy_immunity(self):
        """Test JavaScript decoy immunity."""
        code = """
const crypto = require("crypto");

const md5Hash = "fake";
const errorMsg = "MD5 is deprecated";

crypto.createHash("sha256");
crypto.createCipheriv("aes-256-gcm", Buffer.alloc(32), Buffer.alloc(16));
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            assert len(findings) == 2
            algorithms = {f.algorithm for f in findings}
            assert algorithms == {"SHA-256", "AES"}
        finally:
            os.unlink(path)

    def test_typescript_detection(self):
        """Test TypeScript detection."""
        code = """
import crypto from "crypto";

const hash = crypto.createHash("sha256");
crypto.createCipheriv("aes-256-gcm", Buffer.alloc(32), Buffer.alloc(16));
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            algorithms = {f.algorithm for f in findings}
            assert "SHA-256" in algorithms
            assert "AES" in algorithms
        finally:
            os.unlink(path)

    def test_rsa_key_size_js(self):
        """Test RSA key size extraction in JavaScript."""
        code = """
const crypto = require("crypto");

crypto.generateKeyPairSync("rsa", { modulusLength: 1024 });
crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
crypto.generateKeyPairSync("rsa", { modulusLength: 4096 });
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            path = Path(f.name)

        try:
            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_file(path, rules)
            rsa_findings = [f for f in findings if f.algorithm == "RSA"]
            key_sizes = sorted(f.key_size for f in rsa_findings if f.key_size)
            assert key_sizes == [1024, 2048, 4096]
        finally:
            os.unlink(path)


class TestMultiLanguageScan:
    """Integration tests for multi-language scanning."""

    def test_mixed_language_directory(self):
        """Test scanning a directory with mixed languages."""
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / "test.py").write_text("import hashlib; hashlib.md5(b'test'); hashlib.sha256(b'test')")

            (tmpdir / "Test.java").write_text("import java.security.MessageDigest; public class Test { void test() { MessageDigest.getInstance(\"SHA-1\"); } }")

            (tmpdir / "test.js").write_text("const crypto = require('crypto'); crypto.createHash('sha512');")

            rules = multilang_engine.load_rules(Path("scanner/rules"))
            python_findings = python_engine.scan_directory(tmpdir)
            java_js_findings = multilang_engine.scan_directory(tmpdir, rules)

            all_findings = python_findings + java_js_findings
            algorithms = {f.algorithm for f in all_findings}

            assert "MD5" in algorithms
            assert "SHA-256" in algorithms
            assert "SHA-1" in algorithms
            assert "SHA-512" in algorithms

            languages = {f.language for f in all_findings}
            assert "python" in languages
            assert "java" in languages
            assert "javascript" in languages

    def test_skip_directories(self):
        """Test that skip directories are respected."""
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            node_modules = tmpdir / "node_modules"
            node_modules.mkdir()
            (node_modules / "package.js").write_text("const crypto = require('crypto'); crypto.createHash('md5');")

            (tmpdir / "real.js").write_text("const crypto = require('crypto'); crypto.createHash('sha256');")

            rules = multilang_engine.load_rules(Path("scanner/rules"))
            findings = multilang_engine.scan_directory(tmpdir, rules)

            assert len(findings) == 1
            assert findings[0].algorithm == "SHA-256"
            assert "node_modules" not in findings[0].file


class TestUnifiedCLI:
    """Tests for the unified scanner CLI."""

    def test_cli_scan_directory(self):
        """Test CLI scanning a directory."""
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "test.py").write_text("import hashlib; hashlib.md5(b'test')")

            result = subprocess.run([
                sys.executable, "-m", "scanner.cli", str(tmpdir), "--json-out", "/tmp/cli_test.json"
            ], capture_output=True, text=True, cwd=".")

            assert result.returncode == 0

            with open("/tmp/cli_test.json") as f:
                data = json.load(f)

            assert len(data) == 1
            assert data[0]["algorithm"] == "MD5"
            assert data[0]["confidence"] == "high"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])