import sys
import tomllib
import xml.etree.ElementTree as ET
import json
from dataclasses import dataclass
from pathlib import Path
import yaml
from typing import Optional, Dict, Any, List, Tuple

from scanner.finding import Finding
from scanner.constants import SKIP_DIRS, SCAN_MAX_ARTIFACT_BYTES

DEPENDENCY_RULES_DIR = Path(__file__).parent / "dependency_rules"
DETECTION_METHOD = "dependency_manifest"
ARTIFACT_TYPE = "DEPENDENCY_MANIFEST"
UNKNOWN_ALGORITHM = "UNKNOWN"
LIBRARY_PRIMITIVE = "library"
LEGACY_CONFIDENCE = "unverified"
MAX_MATCHED_CALL_CHARS = 255
REQUIREMENTS_PREFIX = "requirements"
REQUIREMENTS_SUFFIX = ".txt"
MANIFEST_FILENAMES = (
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "Pipfile.lock",
    "poetry.lock",
    "pom.xml"
)
ECOSYSTEM_LANGUAGE = {
    "pypi": "python",
    "npm": "javascript",
    "maven": "java"
}

@dataclass(frozen=True)
class DependencyRecord:
    path: Path
    line: int
    ecosystem: str
    name: str
    version: Optional[str]
    scope: str
    declared: str

@dataclass
class DependencyFinding(Finding):
    artifact_type: str = ARTIFACT_TYPE
    artifact_ref: Optional[str] = None
    package_ecosystem: Optional[str] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None

DependencyRules = Dict[str, Dict[str, Any]]

def normalize_package_name(ecosystem: str, name: str) -> str:
    name = name.lower()
    if ecosystem == "pypi":
        res = []
        for char in name:
            if char in ("-", "_", "."):
                if not res or res[-1] != "-":
                    res.append("-")
            else:
                res.append(char)
        return "".join(res)
    elif ecosystem == "npm":
        return name
    elif ecosystem == "maven":
        return name
    return name

def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)

def load_rules(rules_dir: Optional[Path] = None) -> DependencyRules:
    if rules_dir is None:
        rules_dir = DEPENDENCY_RULES_DIR
    
    rules: DependencyRules = {}
    if not rules_dir.is_dir():
        return rules
        
    for p in sorted(rules_dir.glob("*.yaml")):
        if p.is_file():
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except Exception:
                _warn(f"Failed to parse {p.name}")
                continue
                
            if not isinstance(data, dict):
                _warn(f"No ecosystem in {p.name}")
                continue
            ecosystem = data.get("ecosystem")
            if ecosystem not in ECOSYSTEM_LANGUAGE:
                _warn(f"Invalid or missing ecosystem in {p.name}: {ecosystem}")
                continue
            packages = data.get("packages")
            if not isinstance(packages, list):
                _warn(f"No packages list in {p.name}")
                continue
                
            if ecosystem not in rules:
                rules[ecosystem] = {}
                
            for pkg in packages:
                if not isinstance(pkg, dict):
                    continue
                name = pkg.get("name")
                library = pkg.get("library")
                algorithm = pkg.get("algorithm")
                primitive = pkg.get("primitive")
                weak_by_default = pkg.get("weak_by_default")
                
                if (name is None or library is None or algorithm is None or 
                    primitive is None or not isinstance(weak_by_default, bool)):
                    _warn(f"Skipping invalid package entry in {p.name}")
                    continue
                
                norm_name = normalize_package_name(ecosystem, name)
                rules[ecosystem][norm_name] = pkg

    return rules

def is_manifest(path: Path) -> bool:
    name = path.name
    if name in MANIFEST_FILENAMES:
        return True
    if name.startswith(REQUIREMENTS_PREFIX) and name.endswith(REQUIREMENTS_SUFFIX):
        return True
    return False

def _within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False

def _read_manifest_text(path: Path) -> Optional[str]:
    try:
        st = path.stat()
        if st.st_size > SCAN_MAX_ARTIFACT_BYTES:
            _warn(f"Manifest too large: {path}")
            return None
        return path.read_text(encoding="utf-8")
    except OSError:
        _warn(f"Failed to read {path}")
        return None
    except UnicodeDecodeError:
        _warn(f"Failed to decode {path}")
        return None

def _is_exact_version(spec: str) -> bool:
    if not spec:
        return False
    # letters, digits, ., -, +, _
    # no component equal to x, X, *
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-+_")
    if any(c not in allowed for c in spec):
        return False
    parts = spec.split(".")
    for p in parts:
        if p in ("x", "X", "*"):
            return False
    if not spec[0].isdigit():
        return False
    return True

def _split_requirement(req_str: str) -> Tuple[str, str]:
    # Basic PEP 508 parsing. 
    # Not using regex per AGENT_RULES.md #5.
    req_str = req_str.split(";")[0].strip()
    name = ""
    idx = 0
    while idx < len(req_str):
        c = req_str[idx]
        if c.isalnum() or c in ("-", "_", "."):
            name += c
            idx += 1
        else:
            break
            
    # extras
    if idx < len(req_str) and req_str[idx] == "[":
        while idx < len(req_str) and req_str[idx] != "]":
            idx += 1
        idx += 1
        
    spec = req_str[idx:].replace(" ", "")
    return name, spec

def _parse_requirements_txt(path: Path, text: str) -> List[DependencyRecord]:
    lines = text.splitlines()
    records = []
    scope = path.name
    if scope.endswith(REQUIREMENTS_SUFFIX):
        scope = scope[:-len(REQUIREMENTS_SUFFIX)]
        
    i = 0
    while i < len(lines):
        line_num = i + 1
        line = lines[i].strip()
        while line.endswith("\\") and i + 1 < len(lines):
            i += 1
            line = line[:-1] + lines[i].strip()
        i += 1
        
        # strip inline comments
        comment_idx = -1
        if line.startswith("#"):
            comment_idx = 0
        else:
            # find " #" or "\t#"
            idx = line.find(" #")
            if idx != -1:
                comment_idx = idx
            idx2 = line.find("\t#")
            if idx2 != -1 and (comment_idx == -1 or idx2 < comment_idx):
                comment_idx = idx2
        if comment_idx != -1:
            line = line[:comment_idx].strip()
            
        if not line:
            continue
            
        if line.startswith("-") or line.startswith(".") or line.startswith("/"):
            continue
            
        if "://" in line:
            if " @ " in line:
                name = line.split(" @ ")[0].strip()
                if " " in name:
                    name = name.split()[0]
                records.append(DependencyRecord(
                    path=path, line=line_num, ecosystem="pypi",
                    name=name, version=None, scope=scope, declared=name
                ))
            continue
            
        # strip --hash tokens and extras
        line = line.split("--hash")[0].strip()
        
        name, spec = _split_requirement(line)
        if not name:
            continue
            
        version = None
        if spec.startswith("==="):
            cand = spec[3:]
            if "*" not in cand:
                version = cand
        elif spec.startswith("=="):
            cand = spec[2:]
            if "*" not in cand:
                version = cand
                
        declared = name + spec
        records.append(DependencyRecord(
            path=path, line=line_num, ecosystem="pypi",
            name=name, version=version, scope=scope, declared=declared
        ))
        
    return records

def _parse_pep508_version(spec: str) -> Optional[str]:
    if spec.startswith("==="):
        cand = spec[3:]
        if "*" not in cand:
            return cand
    elif spec.startswith("=="):
        cand = spec[2:]
        if "*" not in cand:
            return cand
    return None

def _parse_pyproject_toml(path: Path, text: str) -> List[DependencyRecord]:
    try:
        data = tomllib.loads(text)
    except Exception:
        _warn(f"Failed to parse TOML in {path}")
        return []
        
    records = []
    
    # project.dependencies
    project = data.get("project", {})
    deps = project.get("dependencies", [])
    if isinstance(deps, list):
        for dep in deps:
            if isinstance(dep, str):
                name, spec = _split_requirement(dep)
                if name:
                    declared = name + spec
                    version = _parse_pep508_version(spec)
                    records.append(DependencyRecord(
                        path=path, line=0, ecosystem="pypi",
                        name=name, version=version, scope="project.dependencies", declared=declared
                    ))
                    
    # project.optional-dependencies
    opt_deps = project.get("optional-dependencies", {})
    if isinstance(opt_deps, dict):
        for extra, extra_deps in opt_deps.items():
            if isinstance(extra_deps, list):
                for dep in extra_deps:
                    if isinstance(dep, str):
                        name, spec = _split_requirement(dep)
                        if name:
                            declared = name + spec
                            version = _parse_pep508_version(spec)
                            records.append(DependencyRecord(
                                path=path, line=0, ecosystem="pypi",
                                name=name, version=version, 
                                scope=f"project.optional-dependencies.{extra}", 
                                declared=declared
                            ))

    # tool.poetry
    tool = data.get("tool", {})
    poetry = tool.get("poetry", {})
    
    def process_poetry_deps(dep_dict: Any, scope: str):
        if not isinstance(dep_dict, dict):
            return
        for name, val in dep_dict.items():
            if name == "python":
                continue
            spec = ""
            if isinstance(val, str):
                spec = val.replace(" ", "")
            elif isinstance(val, dict):
                spec = val.get("version", "").replace(" ", "")
            
            version = None
            if spec.startswith("==") and "*" not in spec:
                version = spec[2:]
            
            if spec and spec[0].isdigit():
                declared = f"{name}=={spec}"
                if not version and "*" not in spec:
                    version = spec
            else:
                declared = f"{name}{spec}"
                
            records.append(DependencyRecord(
                path=path, line=0, ecosystem="pypi",
                name=name, version=version, scope=scope, declared=declared
            ))
            
    process_poetry_deps(poetry.get("dependencies"), "tool.poetry.dependencies")
    process_poetry_deps(poetry.get("dev-dependencies"), "tool.poetry.dev-dependencies")
    
    groups = poetry.get("group", {})
    if isinstance(groups, dict):
        for gname, gval in groups.items():
            if isinstance(gval, dict):
                process_poetry_deps(gval.get("dependencies"), f"tool.poetry.group.{gname}.dependencies")
                
    return records

def _parse_pipfile_lock(path: Path, text: str) -> List[DependencyRecord]:
    try:
        data = json.loads(text)
    except Exception:
        _warn(f"Failed to parse JSON in {path}")
        return []
        
    if not isinstance(data, dict):
        return []
        
    records = []
    for scope in ("default", "develop"):
        deps = data.get(scope, {})
        if isinstance(deps, dict):
            for name, info in deps.items():
                if isinstance(info, dict):
                    ver_str = info.get("version", "")
                    version = None
                    if ver_str.startswith("=="):
                        version = ver_str[2:]
                    declared = f"{name}=={version}" if version else f"{name}{ver_str}"
                    records.append(DependencyRecord(
                        path=path, line=0, ecosystem="pypi",
                        name=name, version=version, scope=scope, declared=declared
                    ))
    return records

def _parse_poetry_lock(path: Path, text: str) -> List[DependencyRecord]:
    try:
        data = tomllib.loads(text)
    except Exception:
        _warn(f"Failed to parse TOML in {path}")
        return []
        
    records = []
    packages = data.get("package", [])
    if isinstance(packages, list):
        for pkg in packages:
            if isinstance(pkg, dict):
                name = pkg.get("name")
                version = pkg.get("version")
                if name and version:
                    records.append(DependencyRecord(
                        path=path, line=0, ecosystem="pypi",
                        name=name, version=version, scope="poetry.lock", declared=f"{name}=={version}"
                    ))
    return records

def _parse_package_json(path: Path, text: str) -> List[DependencyRecord]:
    try:
        data = json.loads(text)
    except Exception:
        _warn(f"Failed to parse JSON in {path}")
        return []
        
    records = []
    for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        deps = data.get(section, {})
        if isinstance(deps, dict):
            for name, spec in deps.items():
                if isinstance(spec, str):
                    if ":" not in spec and "/" not in spec:
                        declared = f"{name}@{spec}"
                    else:
                        declared = name
                    version = spec if _is_exact_version(spec) else None
                    records.append(DependencyRecord(
                        path=path, line=0, ecosystem="npm",
                        name=name, version=version, scope=section, declared=declared
                    ))
    return records

def _parse_package_lock_json(path: Path, text: str) -> List[DependencyRecord]:
    try:
        data = json.loads(text)
    except Exception:
        _warn(f"Failed to parse JSON in {path}")
        return []
        
    records = []
    
    def process_v3_packages(packages: Dict[str, Any]):
        for key, info in packages.items():
            if key == "" or not isinstance(info, dict) or info.get("link") is True:
                continue
            name = key.split("node_modules/")[-1]
            version = info.get("version")
            records.append(DependencyRecord(
                path=path, line=0, ecosystem="npm",
                name=name, version=version, scope="package-lock.json", 
                declared=f"{name}@{version}"
            ))
            
    def process_v1_deps(deps: Dict[str, Any]):
        for name, info in deps.items():
            if not isinstance(info, dict) or info.get("link") is True:
                continue
            version = info.get("version")
            records.append(DependencyRecord(
                path=path, line=0, ecosystem="npm",
                name=name, version=version, scope="package-lock.json",
                declared=f"{name}@{version}"
            ))
            if "dependencies" in info and isinstance(info["dependencies"], dict):
                process_v1_deps(info["dependencies"])

    if "packages" in data and isinstance(data["packages"], dict):
        process_v3_packages(data["packages"])
    elif "dependencies" in data and isinstance(data["dependencies"], dict):
        process_v1_deps(data["dependencies"])
        
    return records

def _parse_pom_xml(path: Path, text: str) -> List[DependencyRecord]:
    upper_text = text.upper()
    if "<!DOCTYPE" in upper_text or "<!ENTITY" in upper_text:
        _warn(f"XML entities found in {path}, refusing to parse")
        return []
        
    try:
        root = ET.fromstring(text)
    except Exception:
        _warn(f"Failed to parse XML in {path}")
        return []
        
    records = []
    
    def strip_ns(tag: str) -> str:
        if tag.startswith("{"):
            return tag.split("}", 1)[1]
        return tag
        
    def find_all_deps(node: ET.Element):
        deps = []
        for child in node:
            if strip_ns(child.tag) == "dependencies":
                for dep in child:
                    if strip_ns(dep.tag) == "dependency":
                        deps.append(dep)
            elif strip_ns(child.tag) == "dependencyManagement":
                for mgmt_child in child:
                    if strip_ns(mgmt_child.tag) == "dependencies":
                        for dep in mgmt_child:
                            if strip_ns(dep.tag) == "dependency":
                                deps.append(dep)
        return deps

    for dep in find_all_deps(root):
        group_id = None
        artifact_id = None
        version_text = None
        for child in dep:
            tag = strip_ns(child.tag)
            if tag == "groupId" and child.text:
                group_id = child.text.strip().lower()
            elif tag == "artifactId" and child.text:
                artifact_id = child.text.strip().lower()
            elif tag == "version" and child.text:
                version_text = child.text.strip()
                
        if group_id and artifact_id:
            name = f"{group_id}:{artifact_id}"
            version = None
            if version_text and version_text and "${" not in version_text and "[" not in version_text and "(" not in version_text and "," not in version_text:
                version = version_text
            declared = f"{name}:{version_text}" if version_text else name
            records.append(DependencyRecord(
                path=path, line=0, ecosystem="maven",
                name=name, version=version, scope="pom.xml", declared=declared
            ))
            
    return records

def parse_manifest(path: Path, text: str) -> List[DependencyRecord]:
    name = path.name
    if name == "package.json":
        return _parse_package_json(path, text)
    if name == "package-lock.json":
        return _parse_package_lock_json(path, text)
    if name == "pyproject.toml":
        return _parse_pyproject_toml(path, text)
    if name == "Pipfile.lock":
        return _parse_pipfile_lock(path, text)
    if name == "poetry.lock":
        return _parse_poetry_lock(path, text)
    if name == "pom.xml":
        return _parse_pom_xml(path, text)
    if name.startswith(REQUIREMENTS_PREFIX) and name.endswith(REQUIREMENTS_SUFFIX):
        return _parse_requirements_txt(path, text)
    return []

def record_to_finding(record: DependencyRecord, rule: Dict[str, Any]) -> DependencyFinding:
    matched_call = f"{record.scope}: {record.declared}"
    if len(matched_call) > MAX_MATCHED_CALL_CHARS:
        matched_call = matched_call[:MAX_MATCHED_CALL_CHARS]
        
    return DependencyFinding(
        file=str(record.path),
        line=record.line,
        matched_call=matched_call,
        library=rule["library"],
        algorithm=rule["algorithm"],
        primitive=rule["primitive"],
        language=ECOSYSTEM_LANGUAGE[record.ecosystem],
        weak_by_default=rule["weak_by_default"],
        confidence=LEGACY_CONFIDENCE,
        key_size=None,
        detection_method=DETECTION_METHOD,
        artifact_type=ARTIFACT_TYPE,
        artifact_ref=str(record.path),
        package_ecosystem=record.ecosystem,
        package_name=normalize_package_name(record.ecosystem, record.name),
        package_version=record.version
    )

def _dedupe_key(finding: DependencyFinding) -> Tuple[str, str, str, str, str, str]:
    return (
        finding.artifact_type,
        finding.artifact_ref or "",
        finding.package_ecosystem or "",
        finding.package_name or "",
        finding.package_version or "",
        finding.algorithm
    )

def scan_file(path: Path, rules: Optional[DependencyRules] = None) -> List[Finding]:
    if rules is None:
        rules = load_rules()
        
    if not is_manifest(path):
        _warn(f"Not a recognised manifest: {path}")
        return []
        
    text = _read_manifest_text(path)
    if text is None:
        return []
        
    records = parse_manifest(path, text)
    findings = []
    seen = set()
    
    for rec in records:
        ecosystem_rules = rules.get(rec.ecosystem, {})
        norm_name = normalize_package_name(rec.ecosystem, rec.name)
        rule = ecosystem_rules.get(norm_name)
        if rule:
            finding = record_to_finding(rec, rule)
            key = _dedupe_key(finding)
            if key not in seen:
                seen.add(key)
                findings.append(finding)
                
    findings.sort(key=lambda f: (f.file, f.line, getattr(f, "package_name", "") or ""))
    # MyPy/type system wants List[Finding] as return. DependencyFinding is a subclass.
    # We can just return the list directly.
    return [f for f in findings]

def _should_skip(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    for part in rel.parts:
        if part in SKIP_DIRS:
            return True
    return False

def scan_directory(root: Path, rules: Optional[DependencyRules] = None) -> List[Finding]:
    if rules is None:
        rules = load_rules()
        
    if root.is_file():
        return scan_file(root, rules)
        
    all_findings = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if not is_manifest(p):
            continue
        if _should_skip(p, root):
            continue
        if not _within_root(p, root):
            _warn(f"Symlink escaping root: {p}")
            continue
            
        all_findings.extend(scan_file(p, rules))
        
    all_findings.sort(key=lambda f: (f.file, f.line, getattr(f, "package_name", "") or ""))
    return all_findings
