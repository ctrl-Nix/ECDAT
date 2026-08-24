# Scanner Skill

Rules:
- Use the ast module for Python scanning.
- Use tree-sitter 0.21.3 for Java and JavaScript scanning.
- Never use regex for scanning logic.
- Use a unified Finding dataclass.
- Keep YAML rules externalized.
- Resolve imports for confidence scoring.
- Extract key_size when possible.

Confidence values:
- "high" when the import is verified.
- "unverified" otherwise.
