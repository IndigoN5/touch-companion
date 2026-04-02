#!/usr/bin/env python3
"""
TLRW META-SUPERVISOR
External validation and deployment gatekeeper for self-healing cycles.

Responsibilities:
    - Maintain SHA256 hash of the last known-good tlrw_fixer.py
    - Run the comprehensive test suite against any proposed patch
    - Approve or reject patches based on test results
    - Archive previous versions before deploying a patch
    - Provide manual rollback capability

Usage:
    python meta_supervisor.py validate <patch_file> <fixer_file>
    python meta_supervisor.py rollback <fixer_file>
    python meta_supervisor.py status
"""

import sys
import os
import json
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.resolve()
STATE_FILE = BASE_DIR / "self_heal_state.json"
ARCHIVE_DIR = BASE_DIR / "archive"
LOG_DIR = BASE_DIR / "logs"
TEST_FILE = BASE_DIR / "test_tlrw_comprehensive.py"

ARCHIVE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "known_good_hash": None,
        "version": 0,
        "history": [],
    }


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_event(event: dict):
    log_file = LOG_DIR / "meta_supervisor.log"
    event["timestamp"] = datetime.now().isoformat()
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, indent=2) + "\n---\n")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(patch_path: Path, fixer_path: Path) -> bool:
    """
    Validate a proposed patch against the comprehensive test suite.

    Steps:
        1. Verify the patch file exists and is parseable Python
        2. Verify the test suite exists
        3. Create a temporary copy of the fixer with the patch applied
        4. Run the test suite against the patched version
        5. If all tests pass: approve, archive old, deploy new
        6. If any test fails: reject, clean up

    Returns True if patch was approved and deployed, False otherwise.
    """
    state = load_state()

    print(f"[META-SUPERVISOR] Validating patch: {patch_path}")
    print(f"[META-SUPERVISOR] Target fixer: {fixer_path}")

    # --- Step 1: Verify patch is valid Python ---
    if not patch_path.exists():
        print("[META-SUPERVISOR] REJECT: Patch file does not exist")
        log_event({"action": "reject", "reason": "patch_not_found", "patch": str(patch_path)})
        return False

    patch_source = patch_path.read_text(encoding="utf-8")
    try:
        compile(patch_source, str(patch_path), "exec")
    except SyntaxError as e:
        print(f"[META-SUPERVISOR] REJECT: Patch has syntax error at line {e.lineno}: {e.msg}")
        log_event({"action": "reject", "reason": "syntax_error", "detail": str(e)})
        return False

    # --- Step 2: Verify test suite exists ---
    if not TEST_FILE.exists():
        print(f"[META-SUPERVISOR] REJECT: Test suite not found at {TEST_FILE}")
        log_event({"action": "reject", "reason": "test_suite_missing"})
        return False

    # --- Step 3: Record current state ---
    if fixer_path.exists():
        current_hash = file_hash(fixer_path)
    else:
        current_hash = None

    patch_hash = hashlib.sha256(patch_source.encode()).hexdigest()

    if current_hash == patch_hash:
        print("[META-SUPERVISOR] SKIP: Patch is identical to current version")
        log_event({"action": "skip", "reason": "identical"})
        return True

    # --- Step 4: Run tests against the patched fixer ---
    # Create a temporary backup
    backup_path = fixer_path.parent / "tlrw_fixer_backup.py"
    if fixer_path.exists():
        shutil.copy2(fixer_path, backup_path)

    # Deploy patch temporarily for testing
    shutil.copy2(patch_path, fixer_path)

    print("[META-SUPERVISOR] Running comprehensive test suite...")
    try:
        # Try pytest first, fall back to unittest
        check = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if check.returncode == 0:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", str(TEST_FILE), "-v", "--tb=short"],
                capture_output=True, text=True, timeout=180,
                cwd=str(BASE_DIR),
            )
        else:
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", TEST_FILE.stem, "-v"],
                capture_output=True, text=True, timeout=180,
                cwd=str(BASE_DIR),
            )
        test_passed = proc.returncode == 0
        test_output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        print("[META-SUPERVISOR] REJECT: Tests timed out")
        test_passed = False
        test_output = "TIMEOUT"

    # --- Step 5/6: Decision ---
    if test_passed:
        print("[META-SUPERVISOR] APPROVED: All tests passed")

        # Archive the old version
        state["version"] += 1
        archive_name = f"tlrw_fixer_v{state['version']}.bak"
        archive_path = ARCHIVE_DIR / archive_name

        if backup_path.exists():
            shutil.copy2(backup_path, archive_path)
            print(f"[META-SUPERVISOR] Archived previous version as {archive_name}")

        # Update state
        state["known_good_hash"] = patch_hash
        state["history"].append({
            "version": state["version"],
            "hash": patch_hash,
            "previous_hash": current_hash,
            "timestamp": datetime.now().isoformat(),
            "action": "approved",
        })
        save_state(state)

        # Clean up
        if backup_path.exists():
            backup_path.unlink()
        if patch_path.exists():
            patch_path.unlink()

        log_event({
            "action": "approve",
            "version": state["version"],
            "hash": patch_hash,
            "previous_hash": current_hash,
        })
        return True
    else:
        print("[META-SUPERVISOR] REJECTED: Tests failed")
        print("[META-SUPERVISOR] Test output:")
        # Print last 30 lines of output
        output_lines = test_output.strip().split("\n")
        for line in output_lines[-30:]:
            print(f"  {line}")

        # Restore the original
        if backup_path.exists():
            shutil.copy2(backup_path, fixer_path)
            backup_path.unlink()
            print("[META-SUPERVISOR] Original fixer restored")

        # Clean up rejected patch
        if patch_path.exists():
            patch_path.unlink()

        state["history"].append({
            "version": state["version"],
            "hash": patch_hash,
            "timestamp": datetime.now().isoformat(),
            "action": "rejected",
            "reason": "tests_failed",
        })
        save_state(state)

        log_event({
            "action": "reject",
            "reason": "tests_failed",
            "hash": patch_hash,
            "test_output_tail": "\n".join(output_lines[-10:]),
        })
        return False


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def rollback(fixer_path: Path):
    """Rollback to the most recent archived version."""
    state = load_state()

    if state["version"] < 1:
        print("[META-SUPERVISOR] No archived versions available for rollback")
        return False

    archive_name = f"tlrw_fixer_v{state['version']}.bak"
    archive_path = ARCHIVE_DIR / archive_name

    if not archive_path.exists():
        print(f"[META-SUPERVISOR] Archive file not found: {archive_name}")
        return False

    shutil.copy2(archive_path, fixer_path)
    print(f"[META-SUPERVISOR] Rolled back to version {state['version']}")

    state["known_good_hash"] = file_hash(fixer_path)
    state["history"].append({
        "version": state["version"],
        "timestamp": datetime.now().isoformat(),
        "action": "rollback",
    })
    save_state(state)

    log_event({"action": "rollback", "version": state["version"]})
    return True


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def show_status():
    """Display current supervisor state."""
    state = load_state()

    print("=" * 50)
    print("  TLRW META-SUPERVISOR STATUS")
    print("=" * 50)
    print(f"  Current Version:   {state['version']}")
    print(f"  Known Good Hash:   {state.get('known_good_hash', 'not set')}")
    print(f"  Archive Dir:       {ARCHIVE_DIR}")
    print(f"  Test Suite:        {'FOUND' if TEST_FILE.exists() else 'MISSING'}")
    print(f"  State File:        {STATE_FILE}")
    print()

    # List archives
    archives = sorted(ARCHIVE_DIR.glob("tlrw_fixer_v*.bak"))
    if archives:
        print("  Archived Versions:")
        for a in archives:
            size = a.stat().st_size
            print(f"    {a.name} ({size:,} bytes)")
    else:
        print("  No archived versions yet")

    # Recent history
    history = state.get("history", [])
    if history:
        print()
        print("  Recent History (last 5):")
        for entry in history[-5:]:
            print(f"    [{entry.get('timestamp', '?')}] "
                  f"v{entry.get('version', '?')} — {entry.get('action', '?')}")

    print("=" * 50)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python meta_supervisor.py validate <patch_file> <fixer_file>")
        print("  python meta_supervisor.py rollback <fixer_file>")
        print("  python meta_supervisor.py status")
        sys.exit(1)

    command = sys.argv[1]

    if command == "validate":
        if len(sys.argv) < 4:
            print("Usage: python meta_supervisor.py validate <patch_file> <fixer_file>")
            sys.exit(1)
        patch_path = Path(sys.argv[2]).resolve()
        fixer_path = Path(sys.argv[3]).resolve()
        success = validate(patch_path, fixer_path)
        sys.exit(0 if success else 1)

    elif command == "rollback":
        if len(sys.argv) < 3:
            print("Usage: python meta_supervisor.py rollback <fixer_file>")
            sys.exit(1)
        fixer_path = Path(sys.argv[2]).resolve()
        success = rollback(fixer_path)
        sys.exit(0 if success else 1)

    elif command == "status":
        show_status()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
