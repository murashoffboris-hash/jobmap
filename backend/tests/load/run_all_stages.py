"""
NFR-001 Full load test cycle runner.
Runs 4 stages: 10 → 100 → 500 → 1000 virtual users.
Each stage: 30s ramp-up + 3 min steady state.

Usage:
    cd backend/tests/load
    python run_all_stages.py

Requires: locust installed (pip install locust)
"""
import subprocess
import sys
import time
from pathlib import Path

HOST = "https://phone.service247.by"
STAGES = [
    {"users": 10,  "rate": 2,  "time": "3m", "label": "10_user"},
    {"users": 100, "rate": 10, "time": "3m", "label": "100_user"},
    {"users": 500, "rate": 20, "time": "3m", "label": "500_user"},
    {"users": 1000,"rate": 30, "time": "3m", "label": "1000_user"},
]
THIS_DIR = Path(__file__).parent


def run_stage(stage: dict) -> bool:
    """Run one locust stage. Returns True on success (no critical errors)."""
    users = stage["users"]
    rate = stage["rate"]
    duration = stage["time"]
    label = stage["label"]
    csv_path = THIS_DIR / f"stats_{label}"

    print(f"\n{'='*60}")
    print(f"STAGE: {users} users (spawn {rate}/s, run {duration})")
    print(f"{'='*60}")

    cmd = [
        "locust",
        "-f", str(THIS_DIR / "locustfile.py"),
        "--host", HOST,
        "--headless",
        "-u", str(users),
        "-r", str(rate),
        "--run-time", duration,
        "--csv", str(csv_path),
        "--html", str(THIS_DIR / f"report_{label}.html"),
        "--print-stats",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    # Print locust output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Check for critical failures in output
    success = result.returncode == 0

    # Also parse the output for failure rates
    for line in (result.stdout or "").splitlines():
        if "FAILURES" in line and "100.0" in line:
            print(f"⚠️  WARNING: 100% failures detected in stage {label}")
            # Don't fail immediately — log it and continue

    print(f"Stage {label}: {'✅ PASS' if success else '❌ FAIL'} (exit code {result.returncode})")
    time.sleep(2)  # cooldown between stages
    return success


def main():
    print("NFR-001 LOAD TEST CYCLE")
    print(f"Target: {HOST}")
    print(f"Stages: {[s['label'] for s in STAGES]}")
    print()

    results = {}
    all_pass = True

    for stage in STAGES:
        ok = run_stage(stage)
        results[stage["label"]] = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    for label, status in results.items():
        print(f"  {label:<15} {status}")
    print(f"{'='*60}")
    print(f"OVERALL: {'✅ ALL PASS' if all_pass else '❌ SOME STAGES FAILED'}")
    print(f"{'='*60}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
