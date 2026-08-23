"""Day-5 deliverable: seed a few hundred findings and time the dashboard query.

Usage (from repo root):
    # against Docker Postgres (default DATABASE_URL):
    python -m backend.db.seed --findings 500

    # against a throwaway SQLite file, no Docker needed:
    python -m backend.db.seed --sqlite --findings 500

Seeds one repo + one scan + N findings, then times the exact query the
dashboard runs most: "findings for this scan, filtered by risk tier."
"""

from __future__ import annotations

import argparse
import os
import random
import time

WEAK = [
    ("MD5", None, "CRITICAL"),
    ("SHA1", None, "HIGH"),
    ("RC4", 128, "HIGH"),
    ("DES", 56, "CRITICAL"),
    ("RSA", 1024, "CRITICAL"),
    ("ECDSA", 256, "MEDIUM"),
    ("AES", 256, "LOW"),
]
CRITICALITIES = ("MEDIUM", "HIGH", "CRITICAL")


def _fake_finding(i: int) -> dict:
    algo, key_size, tier = random.choice(WEAK)
    return {
        "file": f"src/module_{i % 40}/file_{i}.py",
        "line": random.randint(1, 400),
        "algorithm": algo,
        "key_size": key_size,
        "confidence": random.choice(["high", "medium"]),
        "risk_tier": tier,
        "risk_reason": f"{algo} is deprecated / quantum-vulnerable.",
        "criticality": random.choice(CRITICALITIES),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--findings", type=int, default=500)
    parser.add_argument("--sqlite", action="store_true",
                        help="use a local sqlite file instead of DATABASE_URL")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()

    if args.sqlite:
        os.environ["DATABASE_URL"] = "sqlite:///seed_benchmark.db"

    # Import after DATABASE_URL is set so the lazy engine picks it up.
    from sqlalchemy.orm import Session

    from backend.db import crud
    from backend.db.database import get_engine, init_db

    engine = get_engine()
    init_db(engine)  # idempotent
    print(f"Connected: {engine.url}")

    with Session(engine) as session:
        repo = crud.get_or_create_repository(
            session, name="seed-repo", url="https://example.com/seed"
        )
        scan = crud.start_scan(session, repo.id)
        crud.save_findings(session, scan.id, [_fake_finding(i) for i in range(args.findings)])
        crud.complete_scan(session, scan.id)
        session.commit()
        print(f"Seeded {args.findings} findings into scan {scan.id}.")

        best = None
        for _ in range(args.repeats):
            t0 = time.perf_counter()
            rows = crud.get_findings_for_scan(session, scan.id, risk_tier="CRITICAL")
            elapsed = (time.perf_counter() - t0) * 1000
            best = elapsed if best is None else min(best, elapsed)
        print(f"  filtered query returned {len(rows)} rows")
        print(f"  best of {args.repeats}: {best:.2f} ms")

        t0 = time.perf_counter()
        summary = crud.get_risk_summary(session, scan.id)
        print(f"  summary query: {(time.perf_counter() - t0) * 1000:.2f} ms -> {summary}")

    print("Benchmark done. If the filtered query is slow, confirm "
          "idx_findings_scan_id / idx_findings_severity exist (EXPLAIN on Postgres).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
