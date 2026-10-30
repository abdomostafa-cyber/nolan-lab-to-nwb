# PR description for catalystneuro/neuroconv: Neuralynx (for review, edit before use)

> **Branch:** `fix/neuralynx-get-metadata-after-remove-channels`, one commit (`1970afc`) on top of
> `main` at `529e218`. One of the six follow-ups from #2141 (AlphaOmega #2152 merged; Axona #2159 open).
> **Pushed** to the fork on 2026-10-30, ready to open.
> **After opening:** rename `changelog_entries/PRNUMBER.bugfix.md` to `<PR number>.bugfix.md` in a
> second commit.

---

**Title:** Keep `NeuralynxRecordingInterface.get_metadata` working after `remove_channels`

**Body:**

Follow-up to #2141, like #2152 and #2159. `NeuralynxRecordingInterface.get_metadata` calls
`_extract_header_metadata`, which parses the header through `recording_extractor.neo_reader`, so after
`remove_channels` it raises `AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`.

Same approach as #2140: parse the header in `__init__`, while the recording is still the neo extractor.

The test is in `TestNeuralynxRecordingInterfaceV574` (Cheetah 5.7.4, 5 channels), because the stream
in `TestMultiStreamNeuralynxRecordingInterface` has a single channel, and removing it would leave
nothing to check. Side note: the `V574`, `V563` and `V540` classes have no base class and no `test_`
methods, so pytest collects nothing else from them. Their `check_*` methods never run. I left that
alone here; happy to move the test if you'd prefer it elsewhere.

Checked locally:
- the new test fails on `main` and passes with the change;
- the Neuralynx recording tests go from 12 passed + the new test failing to 13 passed, with the same
  Zarr skip;
- `run_conversion` after `remove_channels`, without passing metadata, writes 4 of the 5 channels with
  the start time, session id and device that the `V574` class expects;
- pre-commit hooks pass.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
