"""Break the converter on purpose, one plausible bug at a time, and check that the test suite notices.

Each mutation is a single text replacement in src/. The original file is restored afterwards, even
on failure. A mutation that the suite does not catch ("SURVIVED") is a gap in the tests.

Usage: uv run python scripts/mutation_check.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "nolan_lab_to_nwb"

MUTATIONS = [
    ("analog scaling in millivolts instead of volts", "interfaces.py",
     "return float(gains_uv[0]) * 1e-6", "return float(gains_uv[0]) * 1e-3"),
    ("end-of-file zero padding not trimmed", "converter.py",
     "        if self.padding_samples:\n", "        if False:\n"),
    ("Channel Map read as 0-based (off by one)", "openephys_settings.py",
     'int(channel.get("Mapping")) - 1', 'int(channel.get("Mapping"))'),
    ("Open Ephys counter offset not removed", "converter.py",
     "recording.shift_times(-recording.get_start_time())", "pass"),
    ("pulse edge one sample early", "interfaces.py",
     "rising = np.flatnonzero(~high[:-1] & high[1:]) + 1", "rising = np.flatnonzero(~high[:-1] & high[1:])"),
    ("session start in UTC instead of BST", "metadata.yaml",
     '"2023-04-21T09:55:34+01:00"', '"2023-04-21T09:55:34+00:00"'),
]


def run_tests() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "-m", "not full"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result.returncode == 0


def main() -> None:
    if not run_tests():
        sys.exit("Suite fails on unmodified code; fix that first.")
    survived = 0
    for label, filename, old, new in MUTATIONS:
        path = PKG / filename
        original = path.read_bytes()  # bytes, so line endings are restored exactly
        text = original.decode("utf-8").replace("\r\n", "\n")
        if text.count(old) != 1:
            sys.exit(f"Mutation target not found exactly once in {filename}: {old!r}")
        try:
            path.write_bytes(text.replace(old, new).encode("utf-8"))
            caught = not run_tests()
        finally:
            path.write_bytes(original)
        survived += not caught
        print(f"{'caught  ' if caught else 'SURVIVED'}  {label}")
    print(f"{len(MUTATIONS) - survived}/{len(MUTATIONS)} mutations caught")
    sys.exit(1 if survived else 0)


if __name__ == "__main__":
    main()
