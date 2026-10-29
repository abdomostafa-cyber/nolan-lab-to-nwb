# PR description for catalystneuro/neuroconv: AlphaOmega (for review, edit before use)

> **Status:** opened 2026-10-28 as [catalystneuro/neuroconv#2152](https://github.com/catalystneuro/neuroconv/pull/2152); changelog entry renamed in a second commit.
> **Branch:** `fix/alphaomega-get-metadata-after-remove-channels`, one commit (`af0cf00`) on top of
> `main` at `ea1f362`. First of the six follow-ups the maintainer asked for in #2141, one PR per
> interface, in the same format.
> **After opening:** rename `changelog_entries/PRNUMBER.bugfix.md` to `<PR number>.bugfix.md` in a
> second commit.

---

**Title:** Keep `AlphaOmegaRecordingInterface.get_metadata` working after `remove_channels`

**Body:**

Follow-up to #2141, as discussed there. `AlphaOmegaRecordingInterface.get_metadata` reads the
session start time through `recording_extractor.neo_reader`, so after `remove_channels` it raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`.

Same approach as #2140: read the start time in `__init__`, while the recording is still the neo
extractor. The test mirrors the one in #2140.

Checked locally:
- the new test fails on `main` and passes with the change;
- the AlphaOmega tests in `test_recording_interfaces.py` go from 13 passed + the new test failing to
  14 passed, with the same Zarr skip;
- `run_conversion` after `remove_channels`, without passing metadata, writes 3 of the 4 channels
  with the same start time;
- pre-commit hooks pass.
