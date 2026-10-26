"""NWB Inspector: nothing at BEST_PRACTICE_VIOLATION or above, except the documented exceptions."""

from __future__ import annotations

from nwbinspector import Importance, inspect_nwbfile

# check name -> why it is left (README, "NWB Inspector report")
DOCUMENTED_EXCEPTIONS = {
    "check_subject_age": "The dataset reports neither age nor date of birth; not guessed.",
}


def test_no_unexplained_issues(converted_fixture):
    _, path = converted_fixture
    messages = list(inspect_nwbfile(nwbfile_path=path, importance_threshold=Importance.BEST_PRACTICE_VIOLATION))
    unexplained = [m for m in messages if m.check_function_name not in DOCUMENTED_EXCEPTIONS]
    assert not unexplained, "\n".join(f"{m.importance.name} {m.check_function_name}: {m.message}" for m in unexplained)


def test_documented_exceptions_still_apply(converted_fixture):
    """If an exception stops firing (e.g. age gets added), remove it from the list and the README."""
    _, path = converted_fixture
    fired = {m.check_function_name for m in inspect_nwbfile(nwbfile_path=path)}
    assert set(DOCUMENTED_EXCEPTIONS) <= fired
