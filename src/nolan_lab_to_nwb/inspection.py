"""Run NWB Inspector and fail on anything not documented as intentionally left.

``nwbinspector`` 0.7.2's CLI exits 0 even when it reports CRITICAL issues, so it cannot gate CI on
its own. ``python -m nolan_lab_to_nwb.inspection FILE.nwb`` prints the report and exits 1 on any
message at BEST_PRACTICE_VIOLATION or above that is not listed below.
"""

from __future__ import annotations

import sys
from pathlib import Path

from nwbinspector import Importance, InspectorMessage, format_messages, inspect_nwbfile

# check name -> why it is left; mirrored in the README table "NWB Inspector report".
DOCUMENTED_EXCEPTIONS = {
    "check_subject_age": (
        "The dataset reports neither age nor date of birth, no publication covers this animal, and "
        "the lab's papers disagree on age, sex and strain, so nothing is guessed. Asked the lab."
    ),
}


def unexplained_messages(nwbfile_path: str | Path) -> tuple[list[InspectorMessage], list[InspectorMessage]]:
    """Return (all messages at BEST_PRACTICE_VIOLATION or above, the ones not in DOCUMENTED_EXCEPTIONS)."""
    messages = list(inspect_nwbfile(nwbfile_path=nwbfile_path, importance_threshold=Importance.BEST_PRACTICE_VIOLATION))
    return messages, [m for m in messages if m.check_function_name not in DOCUMENTED_EXCEPTIONS]


def main(argv: list[str] | None = None) -> None:
    paths = argv if argv is not None else sys.argv[1:]
    if not paths:
        sys.exit("usage: python -m nolan_lab_to_nwb.inspection FILE.nwb [FILE.nwb ...]")
    failed = False
    for path in paths:
        messages, unexplained = unexplained_messages(path)
        print("\n".join(format_messages(messages)) if messages else f"{path}: no issues")
        for message in messages:
            if message.check_function_name in DOCUMENTED_EXCEPTIONS:
                print(f"documented exception {message.check_function_name}: "
                      f"{DOCUMENTED_EXCEPTIONS[message.check_function_name]}")
        failed |= bool(unexplained)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
