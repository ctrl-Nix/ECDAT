# AGENT_RULES.md — read automatically by all coding agents in this repo.
# Every AI agent working on this codebase must follow these rules without
# exception. If a task conflicts with a rule, stop and flag a human — do not
# silently work around it.
1. Before writing any code, read the assigned feature's spec doc in full,
including its "Required Context Files" list — open those files first.
2. Never modify a file outside your feature's declared "File Ownership" list
without flagging a human first.
3. Follow "Concrete Interface Definitions" literally. Do not rename, restructure,
or "improve" a signature without flagging it — even if you think your version
is better.
4. If you hit a situation not covered by "Pre-Answered Ambiguities," stop and ask
a human. Do not guess.
5. Crypto detection uses Python's `ast` module for Python and tree-sitter +
YAML rules for Java/JavaScript. Never use regex for source-code scanning.
6. Current scope (updated): source-code scanning (Python/Java/JavaScript),
binary scanning (heuristic), container image scanning, and third-party
dependency scanning are ALL in scope as of this sprint. Do not claim any
scanner covers more than what its own spec describes.
7. Run the exact commands in the spec's "Test Plan" before declaring a task done.
8. Commit only to your assigned feature branch. Never commit directly to main.
9. If something looks unimplemented that a spec assumes exists, say so — do not
silently stub it out or fake success.