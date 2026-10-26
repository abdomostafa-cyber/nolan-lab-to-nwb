"""NWB Inspector: nothing at BEST_PRACTICE_VIOLATION or above, except the documented exceptions."""

from __future__ import annotations

import pytest
from nwbinspector import inspect_nwbfile

from nolan_lab_to_nwb.inspection import DOCUMENTED_EXCEPTIONS, unexplained_messages


def test_no_unexplained_issues(converted_fixture):
    _, path = converted_fixture
    _, unexplained = unexplained_messages(path)
    assert not unexplained, "\n".join(f"{m.importance.name} {m.check_function_name}: {m.message}" for m in unexplained)


def test_documented_exceptions_still_apply(converted_fixture):
    """If an exception stops firing (e.g. age gets added), remove it from the list and the README."""
    _, path = converted_fixture
    fired = {m.check_function_name for m in inspect_nwbfile(nwbfile_path=path)}
    assert set(DOCUMENTED_EXCEPTIONS) <= fired


def test_gate_exits_nonzero_on_unexplained_issue(tmp_path, converted_fixture, monkeypatch):
    """The CI gate must fail when a new issue appears (here: the documented one, un-documented)."""
    from nolan_lab_to_nwb import inspection

    _, path = converted_fixture
    monkeypatch.setattr(inspection, "DOCUMENTED_EXCEPTIONS", {})
    with pytest.raises(SystemExit) as exit_info:
        inspection.main([str(path)])
    assert exit_info.value.code == 1
