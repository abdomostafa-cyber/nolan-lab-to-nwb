# PR description for catalystneuro/neuroconv: MaxOne (for review, edit before use)

> **Branch:** `fix/maxone-get-metadata-after-remove-channels`, one commit (`cceb1a3`) on top of
> `main` at `529e218`. One of the six follow-ups from #2141 (AlphaOmega, #2152, is merged).
> **After opening:** rename `changelog_entries/PRNUMBER.bugfix.md` to `<PR number>.bugfix.md` in a
> second commit.
> **Not a ready PR — ask first.** `TestMaxOneRecordingInterface` is skipped unconditionally
> (`@pytest.mark.skip(reason="This interface fails to load the necessary plugin sometimes.")`) and the
> interface is `# pragma: no cover`, so the new test would never run. Raise it as a question on the
> PR thread before opening anything.

---

**Title:** Keep `MaxOneRecordingInterface.get_metadata` working after `remove_channels`

**Body:**

Follow-up to #2141, like #2152. `MaxOneRecordingInterface.get_metadata` reads the Maxwell version
through `recording_extractor.neo_reader`, so after `remove_channels` it raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`.

Same approach as #2140: read the version in `__init__`, while the recording is still the neo extractor.

`TestMaxOneRecordingInterface` is skipped, so the new test there will not run in CI. I checked the
change on Windows by bypassing the Linux check for an experiment: on `main` `get_metadata` fails
after `remove_channels`, and with the change it returns the same `Devices`. Pre-commit hooks pass.
