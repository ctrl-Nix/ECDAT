import pytest
import os
import sys
import json
from pathlib import Path
from dataclasses import asdict

from scanner import dependency_engine
from scanner.cli import main

def test_is_manifest_matches_only_supported_filenames():
    valid = ["requirements.txt", "requirements-dev.txt", "requirements_prod.txt", 
             "pyproject.toml", "Pipfile.lock", "poetry.lock", "package.json", 
             "package-lock.json", "pom.xml"]
    invalid = ["README.txt", "requirements.md", "package.json.bak", "Pipfile", "yarn.lock", "build.gradle"]
    
    for f in valid:
        assert dependency_engine.is_manifest(Path(f))
    for f in invalid:
        assert not dependency_engine.is_manifest(Path(f))

def test_normalize_package_name_per_ecosystem():
    norm = dependency_engine.normalize_package_name
    assert norm("pypi", "PyCrypto") == "pycrypto"
    assert norm("pypi", "Py_Crypto.Dome") == "py-crypto-dome"
    assert norm("npm", "@Scope/Name") == "@scope/name"
    assert norm("npm", "Crypto-JS") == "crypto-js"
    assert norm("maven", "Org.BouncyCastle:BCProv-JDK18on") == "org.bouncycastle:bcprov-jdk18on"

def test_load_rules_reads_the_shipped_packs():
    rules = dependency_engine.load_rules()
    assert "pypi" in rules
    assert "npm" in rules
    assert "pycrypto" in rules["pypi"]
    assert "md5" in rules["npm"]
    
    rule = rules["pypi"]["pycrypto"]
    for k in ("name", "library", "algorithm", "primitive", "weak_by_default"):
        assert k in rule

def test_load_rules_skips_bad_files_and_entries_with_warnings(tmp_path, capsys):
    (tmp_path / "pypi.yaml").write_text('''
ecosystem: pypi
packages:
  - name: good
    library: good
    algorithm: MD5
    primitive: hash
    weak_by_default: true
  - name: bad1
    library: bad1
    primitive: hash
    weak_by_default: true
  - name: bad2
    library: bad2
    algorithm: MD5
    primitive: hash
    weak_by_default: "yes"
''', encoding="utf-8")
    (tmp_path / "noeco.yaml").write_text("packages: []\n", encoding="utf-8")
    (tmp_path / "bad.yaml").write_text("not yaml: [", encoding="utf-8")
    
    rules = dependency_engine.load_rules(tmp_path)
    assert "pypi" in rules
    assert "good" in rules["pypi"]
    assert "bad1" not in rules["pypi"]
    assert "bad2" not in rules["pypi"]
    
    err = capsys.readouterr().err
    assert err.count("[warn]") == 4

def test_requirements_txt_pinned_pycrypto_emits_unknown_algorithm_finding(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("pycrypto==2.6.1\nrequests==2.31.0\n", encoding="utf-8")
    
    findings = dependency_engine.scan_file(req)
    assert len(findings) == 1
    f = findings[0]
    assert f.line == 1
    assert f.matched_call == "requirements: pycrypto==2.6.1"
    assert f.algorithm == "UNKNOWN"
    assert f.primitive == "library"
    assert f.library == "pycrypto"
    assert f.language == "python"
    assert f.weak_by_default is True
    assert f.confidence == "unverified"
    assert f.key_size is None
    assert f.detection_method == "dependency_manifest"
    assert getattr(f, "artifact_type") == "DEPENDENCY_MANIFEST"
    assert getattr(f, "artifact_ref") == str(req)
    assert getattr(f, "package_ecosystem") == "pypi"
    assert getattr(f, "package_name") == "pycrypto"
    assert getattr(f, "package_version") == "2.6.1"
    
    d = asdict(f)
    for k in ("artifact_type", "artifact_ref", "package_ecosystem", "package_name", "package_version"):
        assert k in d

def test_requirements_txt_ignores_noise_and_never_leaks_urls_or_hashes(tmp_path):
    req = tmp_path / "requirements.txt"
    content = """# comment
-r base.txt
--index-url https://example.com/
-e .
./local/pkg
git+https://example.com/x.git#egg=x
pycrypto==2.6.1\\
    --hash=sha256:aaaa
pycryptodome==3.20.0  # inline comment
cryptography[ssh]==41.0.7 ; python_version >= "3.8"
pyopenssl @ https://example.com/pyopenssl.whl
"""
    req.write_text(content, encoding="utf-8")
    
    findings = dependency_engine.scan_file(req)
    assert len(findings) == 4
    
    tuples = [(f.line, getattr(f, "package_name"), getattr(f, "package_version"), f.matched_call) for f in findings]
    
    # Ordered by (file, line, package_name)
    assert (7, "pycrypto", "2.6.1", "requirements: pycrypto==2.6.1") in tuples
    assert (9, "pycryptodome", "3.20.0", "requirements: pycryptodome==3.20.0") in tuples
    assert (10, "cryptography", "41.0.7", "requirements: cryptography==41.0.7") in tuples
    assert (11, "pyopenssl", None, "requirements: pyopenssl") in tuples
    
    for f in findings:
        assert "://" not in f.matched_call
        assert "hash" not in f.matched_call

def test_requirements_txt_ranges_and_wildcards_leave_version_unset(tmp_path):
    req = tmp_path / "requirements-dev.txt"
    req.write_text("pycryptodome>=3.10,<4\nPyCryptodomex==3.*\n", encoding="utf-8")
    
    findings = dependency_engine.scan_file(req)
    assert len(findings) == 2
    tuples = [(f.line, getattr(f, "package_name"), getattr(f, "package_version"), f.matched_call) for f in findings]
    
    assert (1, "pycryptodome", None, "requirements-dev: pycryptodome>=3.10,<4") in tuples
    assert (2, "pycryptodomex", None, "requirements-dev: PyCryptodomex==3.*") in tuples

def test_package_json_sections_and_exact_version_predicate(tmp_path):
    req = tmp_path / "package.json"
    data = {
        "dependencies": {"md5": "2.3.0", "sha1": "^1.1.1", "left-pad": "1.3.0"},
        "devDependencies": {"crypto-js": "git+https://example.com/crypto-js.git"},
        "optionalDependencies": {"node-forge": "1.x"},
        "peerDependencies": "not-an-object"
    }
    req.write_text(json.dumps(data), encoding="utf-8")
    
    findings = dependency_engine.scan_file(req)
    assert len(findings) == 4
    for f in findings:
        assert f.line == 0
        
    calls = [f.matched_call for f in findings]
    assert "dependencies: md5@2.3.0" in calls
    assert "dependencies: sha1@^1.1.1" in calls
    assert "devDependencies: crypto-js" in calls
    assert "optionalDependencies: node-forge@1.x" in calls
    
    exact = dependency_engine._is_exact_version
    assert exact("2.3.0")
    assert exact("1.0.0-beta.1")
    assert not exact("^2.3.0")
    assert not exact(">=1")
    assert not exact("1.x")
    assert not exact("*")
    assert not exact("latest")
    assert not exact("")

def test_package_lock_json_v3_and_v1_shapes(tmp_path):
    req_v3 = tmp_path / "package-lock.json"
    data_v3 = {
        "packages": {
            "": {},
            "node_modules/md5": {"version": "2.3.0"},
            "node_modules/foo/node_modules/sha1": {"version": "1.1.1"},
            "node_modules/crypto-js": {"link": True},
            "node_modules/node-forge": {"version": "1.3.1"}
        }
    }
    req_v3.write_text(json.dumps(data_v3), encoding="utf-8")
    findings = dependency_engine.scan_file(req_v3)
    assert len(findings) == 3
    calls = [f.matched_call for f in findings]
    assert "package-lock.json: md5@2.3.0" in calls
    assert "package-lock.json: node-forge@1.3.1" in calls
    assert "package-lock.json: sha1@1.1.1" in calls
    
    data_v1 = {
        "dependencies": {
            "md5": {
                "version": "2.3.0",
                "dependencies": {
                    "sha1": {"version": "1.1.1"}
                }
            }
        }
    }
    (tmp_path / "package-lock.json").write_text(json.dumps(data_v1), encoding="utf-8")
    findings = dependency_engine.scan_file(tmp_path / "package-lock.json")
    assert len(findings) == 2
    calls = [f.matched_call for f in findings]
    assert "package-lock.json: md5@2.3.0" in calls
    assert "package-lock.json: sha1@1.1.1" in calls

def test_pyproject_toml_pep621_and_poetry_tables(tmp_path):
    req = tmp_path / "pyproject.toml"
    content = """
[project]
dependencies = ["cryptography>=41", "requests"]
[project.optional-dependencies]
dev = ["pycryptodome==3.20.0"]
[tool.poetry.dependencies]
python = "^3.11"
pycrypto = "2.6.1"
pyopenssl = {version = "^24.0", extras = ["x"]}
[tool.poetry.group.test.dependencies]
pycryptodomex = "3.19.0"
"""
    req.write_text(content, encoding="utf-8")
    findings = dependency_engine.scan_file(req)
    assert len(findings) == 5
    for f in findings:
        assert f.line == 0
        
    tuples = [(getattr(f, "package_name"), getattr(f, "package_version"), f.matched_call) for f in findings]
    assert ("cryptography", None, "project.dependencies: cryptography>=41") in tuples
    assert ("pycryptodome", "3.20.0", "project.optional-dependencies.dev: pycryptodome==3.20.0") in tuples
    assert ("pycrypto", "2.6.1", "tool.poetry.dependencies: pycrypto==2.6.1") in tuples
    assert ("pyopenssl", None, "tool.poetry.dependencies: pyopenssl^24.0") in tuples
    assert ("pycryptodomex", "3.19.0", "tool.poetry.group.test.dependencies: pycryptodomex==3.19.0") in tuples

def test_pipfile_lock_and_poetry_lock(tmp_path):
    req_pip = tmp_path / "Pipfile.lock"
    data_pip = {
        "default": {"pycrypto": {"version": "==2.6.1"}},
        "develop": {"cryptography": {"version": "==41.0.7"}, "requests": {"version": "==2.31.0"}}
    }
    req_pip.write_text(json.dumps(data_pip), encoding="utf-8")
    findings = dependency_engine.scan_file(req_pip)
    assert len(findings) == 2
    tuples = [(getattr(f, "package_name"), getattr(f, "package_version"), f.matched_call) for f in findings]
    assert ("cryptography", "41.0.7", "develop: cryptography==41.0.7") in tuples
    assert ("pycrypto", "2.6.1", "default: pycrypto==2.6.1") in tuples
    
    req_poetry = tmp_path / "poetry.lock"
    content = """
[[package]]
name = "pycryptodome"
version = "3.20.0"

[[package]]
name = "requests"
version = "2.31.0"
"""
    req_poetry.write_text(content, encoding="utf-8")
    findings = dependency_engine.scan_file(req_poetry)
    assert len(findings) == 1
    assert getattr(findings[0], "package_name") == "pycryptodome"
    assert getattr(findings[0], "package_version") == "3.20.0"

def test_non_crypto_packages_produce_no_findings(tmp_path):
    req1 = tmp_path / "requirements.txt"
    req1.write_text("requests==2.31.0\nflask>=3\n", encoding="utf-8")
    req2 = tmp_path / "package.json"
    req2.write_text('{"dependencies": {"left-pad": "1.3.0", "lodash": "4.0.0"}}', encoding="utf-8")
    
    assert dependency_engine.scan_directory(tmp_path) == []

def test_malformed_manifests_return_empty_without_raising(tmp_path, capsys):
    dirs = ["json1", "toml1", "json2", "json3", "txt1", "txt2"]
    for d in dirs:
        (tmp_path / d).mkdir()
        
    (tmp_path / "json1" / "package.json").write_text("{ not json", encoding="utf-8")
    (tmp_path / "toml1" / "pyproject.toml").write_text("[[[", encoding="utf-8")
    (tmp_path / "json2" / "package-lock.json").write_text("[]", encoding="utf-8")
    (tmp_path / "json3" / "Pipfile.lock").write_text('"str"', encoding="utf-8")
    (tmp_path / "txt1" / "requirements.txt").write_bytes(b"\xff\xfe\x00pycrypto")
    (tmp_path / "txt2" / "requirements.txt").write_text("", encoding="utf-8")
    
    for d in dirs:
        assert dependency_engine.scan_directory(tmp_path / d) == []
        
    err = capsys.readouterr().err
    assert err.count("[warn]") == 3

def test_oversize_manifest_is_skipped_with_warning(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(dependency_engine, "SCAN_MAX_ARTIFACT_BYTES", 10)
    req = tmp_path / "requirements.txt"
    req.write_text("pycrypto==2.6.1\n", encoding="utf-8")
    
    assert dependency_engine.scan_file(req) == []
    err = capsys.readouterr().err
    assert "[warn]" in err

def test_duplicate_declarations_are_deduplicated_by_c23_key(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("pycrypto==2.6.1\nPyCrypto==2.6.1\npycrypto==2.7\n", encoding="utf-8")
    
    findings = dependency_engine.scan_file(req)
    assert len(findings) == 2
    tuples = [(f.line, getattr(f, "package_version")) for f in findings]
    assert (1, "2.6.1") in tuples
    assert (3, "2.7") in tuples
    
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "pyproject.toml").write_text('[project]\ndependencies=["pycrypto==2.6.1"]', encoding="utf-8")
    
    all_findings = dependency_engine.scan_directory(tmp_path)
    # 2 from requirements.txt, 1 from pyproject.toml -> total 3 findings
    assert len(all_findings) == 3
    vers = [getattr(f, "package_version") for f in all_findings]
    assert vers.count("2.6.1") == 2
    assert vers.count("2.7") == 1

def test_scan_directory_skips_skip_dirs_and_escaping_symlinks(tmp_path, capsys):
    (tmp_path / "requirements.txt").write_text("pycrypto==2.6.1\n", encoding="utf-8")
    
    (tmp_path / "node_modules" / "md5").mkdir(parents=True)
    (tmp_path / "node_modules" / "md5" / "package.json").write_text('{"dependencies":{"md5":"2.3.0"}}', encoding="utf-8")
    
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "requirements.txt").write_text("pycrypto==2.6.1\n", encoding="utf-8")
    
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "package.json").write_text('{"dependencies":{"md5":"2.3.0"}}', encoding="utf-8")
    
    outside = tmp_path.parent / "outside_dir_xyz"
    outside.mkdir(exist_ok=True)
    (outside / "package.json").write_text('{"dependencies":{"sha1":"1.1.1"}}', encoding="utf-8")
    
    (tmp_path / "linked").mkdir()
    try:
        os.symlink(outside / "package.json", tmp_path / "linked" / "package.json")
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported")
        
    findings = dependency_engine.scan_directory(tmp_path)
    rels = {str(Path(f.file).relative_to(tmp_path)).replace("\\", "/") for f in findings}
    assert rels == {"requirements.txt", "sub/package.json"}
    
    err = capsys.readouterr().err
    assert err.count("[warn]") == 1

def test_output_is_sorted_and_engine_writes_nothing_to_stdout(tmp_path, capsys):
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "package.json").write_text('{"dependencies":{"md5":"2.3.0"}}', encoding="utf-8")
    
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "requirements.txt").write_text("pycrypto==2.6.1\n", encoding="utf-8")
    
    (tmp_path / "requirements.txt").write_text("pycrypto==2.6.1\n", encoding="utf-8")
    
    findings = dependency_engine.scan_directory(tmp_path)
    assert len(findings) == 3
    
    # check sorted by (file, line, package_name)
    assert findings == sorted(findings, key=lambda f: (f.file, f.line, getattr(f, "package_name") or ""))
    
    out = capsys.readouterr().out
    assert out == ""

def test_cli_scan_type_dependency_emits_scored_artifact_findings(tmp_path, capsys):
    (tmp_path / "requirements.txt").write_text("pycrypto==2.6.1\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"dependencies":{"md5":"^2.3.0"}}', encoding="utf-8")
    (tmp_path / "legacy.py").write_text("import hashlib\nhashlib.md5(b'x')\n", encoding="utf-8")
    
    assert main([str(tmp_path), "--scan-type", "dependency"]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    for f in parsed:
        assert f["detection_method"] == "dependency_manifest"
        assert f["artifact_type"] == "DEPENDENCY_MANIFEST"
        if f["package_name"] == "md5":
            assert f["risk_tier"] == "CRITICAL"
            assert f["package_version"] is None
        elif f["package_name"] == "pycrypto":
            assert f["risk_tier"] == "UNSCORED"
            assert f["package_version"] == "2.6.1"
            
    assert main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert parsed[0]["file"].endswith("legacy.py")
    assert parsed[0].get("artifact_type", "SOURCE_FILE") == "SOURCE_FILE"
    
    assert main([str(tmp_path), "--scan-type", "source", "--scan-type", "dependency"]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 3

def test_cli_redact_paths_rewrites_artifact_ref(tmp_path, capsys):
    (tmp_path / "requirements.txt").write_text("pycrypto==2.6.1\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"dependencies":{"md5":"^2.3.0"}}', encoding="utf-8")
    (tmp_path / "legacy.py").write_text("import hashlib\nhashlib.md5(b'x')\n", encoding="utf-8")
    
    main([str(tmp_path), "--scan-type", "dependency", "--redact-paths"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    for f in parsed:
        assert not Path(f["artifact_ref"]).is_absolute()
        assert str(tmp_path).replace("\\", "\\\\") not in out
        
    main([str(tmp_path), "--scan-type", "dependency"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    for f in parsed:
        if "artifact_ref" in f and f["artifact_ref"]:
            assert Path(f["artifact_ref"]).is_absolute()
            assert str(tmp_path) in f["artifact_ref"]

def test_pom_xml_declared_bouncycastle_dependencies(tmp_path):
    pom = tmp_path / "pom.xml"
    content = """<project xmlns="http://maven.apache.org/POM/4.0.0">
    <dependencies>
        <dependency>
            <groupId>org.bouncycastle</groupId>
            <artifactId>bcprov-jdk18on</artifactId>
            <version>1.77</version>
        </dependency>
        <dependency>
            <groupId>org.bouncycastle</groupId>
            <artifactId>bcprov-jdk15on</artifactId>
            <version>${bc.version}</version>
        </dependency>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13</version>
        </dependency>
    </dependencies>
</project>"""
    pom.write_text(content, encoding="utf-8")
    findings = dependency_engine.scan_file(pom)
    assert len(findings) == 2
    for f in findings:
        assert f.language == "java"
        assert getattr(f, "package_ecosystem") == "maven"
        assert f.line == 0
        
    tuples = [(getattr(f, "package_name"), getattr(f, "package_version")) for f in findings]
    assert ("org.bouncycastle:bcprov-jdk15on", None) in tuples
    assert ("org.bouncycastle:bcprov-jdk18on", "1.77") in tuples

def test_pom_xml_doctype_is_rejected_before_parsing(tmp_path, monkeypatch, capsys):
    pom = tmp_path / "pom.xml"
    content = """<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><project><dependencies></dependencies></project>"""
    pom.write_text(content, encoding="utf-8")
    
    def mock_fromstring(*args, **kwargs):
        raise AssertionError("should not be called")
        
    import xml.etree.ElementTree as ET
    monkeypatch.setattr(ET, "fromstring", mock_fromstring)
    
    findings = dependency_engine.scan_file(pom)
    assert findings == []
    
    err = capsys.readouterr().err
    assert "[warn]" in err
