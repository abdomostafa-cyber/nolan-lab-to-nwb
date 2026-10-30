# Issue for catalystneuro/neuroconv: MaxOne (for review, edit before use)

> **Status:** posted 2026-10-30 as [catalystneuro/neuroconv#2170](https://github.com/catalystneuro/neuroconv/issues/2170), via the bug-report form.

> **Route:** an issue, not a PR or a comment. The fix branch is ready, but its test would never
> run (`TestMaxOneRecordingInterface` is `@pytest.mark.skip`ped and the interface is
> `# pragma: no cover`), so the maintainer decides whether they want the PR. An issue records the bug
> even if they say no, and it doesn't pull an open PR (#2159) or a merged one off-topic.
> **Branch:** `fix/maxone-get-metadata-after-remove-channels`, one commit (`cceb1a3`) on top of
> `main` at `529e218`. Not pushed. If they want the PR, push it and use the PR body below.

---

**Issue title:** `MaxOneRecordingInterface.get_metadata` fails after `remove_channels`

**Issue body:**

Same bug as #2140, in `MaxOneRecordingInterface`: `get_metadata` reads the Maxwell version through
`recording_extractor.neo_reader`, so after `remove_channels` it raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`.

I have a fix in the same style as #2152 and #2159 (read the version in `__init__`), plus a test, but
`TestMaxOneRecordingInterface` is skipped ("This interface fails to load the necessary plugin
sometimes"), so the test wouldn't run in CI. I checked it by hand on Windows, bypassing the Linux-only
check: on `main`, `get_metadata` fails after `remove_channels`, and with the change it returns the
same `Devices`.

Would you like a PR for it anyway, or should it wait until the test class can run?

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR body, only if they want the PR

**Title:** Keep `MaxOneRecordingInterface.get_metadata` working after `remove_channels`

**Body:**

Closes #2170. Follow-up to #2141, like #2152 and #2159. `MaxOneRecordingInterface.get_metadata` reads the Maxwell version
through `recording_extractor.neo_reader`, so after `remove_channels` it raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`.

Same approach as #2140: read the version in `__init__`, while the recording is still the neo extractor.

`TestMaxOneRecordingInterface` is skipped, so the new test there will not run in CI. I checked the
change on Windows by bypassing the Linux check for an experiment: on `main` `get_metadata` fails
after `remove_channels`, and with the change it returns the same `Devices`. Pre-commit hooks pass.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
