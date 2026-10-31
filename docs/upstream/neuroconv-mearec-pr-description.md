# PR description for catalystneuro/neuroconv: MEArec (for review, edit before use)

> **Branch:** `fix/mearec-get-metadata-after-remove-channels`, one commit (`60dd307`) on top of
> `main` at `529e218`. One of the six follow-ups from #2141 (AlphaOmega #2152 merged; Axona #2159 open).
> **Status:** opened 2026-10-30 as [catalystneuro/neuroconv#2167](https://github.com/catalystneuro/neuroconv/pull/2167); changelog entry renamed in a second commit (`09308da`).
> Merged by h-mayorquin on 2026-10-31 as `b632975`, code unchanged.
> **After opening:** rename `changelog_entries/PRNUMBER.bugfix.md` to `<PR number>.bugfix.md` in a
> second commit.

---

**Title:** Keep `MEArecRecordingInterface.get_metadata` working after `remove_channels`

**Body:**

Follow-up to #2141, like #2152 and #2159. `MEArecRecordingInterface.get_metadata` reads the simulation info
(device name and recording parameters) through `recording_extractor.neo_reader`, so after
`remove_channels` it raises `AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`.

Same approach as #2140: read the info in `__init__`, while the recording is still the neo extractor.
MEArec files have no session start time, so the test compares the `Devices` metadata instead.

Checked locally:
- the new test fails on `main` and passes with the change;
- the MEArec tests in `test_recording_interfaces.py` go from 12 passed + the new test failing to
  13 passed, with the same Zarr skip;
- `run_conversion` after `remove_channels` (with a `session_start_time` supplied, which MEArec
  conversions need either way) writes 31 of the 32 channels with the same device;
- pre-commit hooks pass.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
