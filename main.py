"""
Main FastAPI Backend Application for ECDAT (PS 26164).
"""

from fastapi import FastAPI
from remediation import get_remediation_text

app = FastAPI(
    title="ECDAT Backend",
    description="Engine for Cryptographic Inventory & Quantum-Risk Assessment",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """Root endpoint verifying backend service status."""
    return {"message": "ECDAT backend running"}


@app.get("/scans/{scan_id}/remediation/{finding_id}")
def get_remediation_for_finding(scan_id: int, finding_id: int):
    """
    Fetch remediation text for one finding. Owned by Shreyanshi per ARCHITECTURE.md.

    NOTE: Currently uses a hardcoded fake finding (MD5 in auth.py:42) pending integration
    with Ronak's real GET /scans/{id} database query output once ready.
    """
    fake_finding = {"algorithm": "MD5", "file": "auth.py", "line": 42}

    remediation_result = get_remediation_text(
        algorithm=fake_finding["algorithm"],
        file=fake_finding["file"],
        line=fake_finding["line"],
    )
    return remediation_result

