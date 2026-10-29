# PR description for catalystneuro/neuroconv: Axona (for review, edit before use)

> **Branch:** `fix/axona-get-metadata-after-remove-channels`, one commit (`961d589`) on top of
> `main` at `189935f`. Second of the six follow-ups from #2141, after AlphaOmega (#2152).
> **After opening:** rename `changelog_entries/PRNUMBER.bugfix.md` to `<PR number>.bugfix.md` in a
> second commit.

---

**Title:** Keep `AxonaRecordingInterface.get_metadata` working after `remove_channels`

**Body:**

Follow-up to #2141, like #2152. `AxonaRecordingInterface.get_metadata` calls
`extract_nwb_file_metadata`, which reads the session start time through
`recording_extractor.neo_reader`, so after `remove_channels` it raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`.

Same approach as #2140: read the start time in `__init__`, next to the existing read of the `.set`
header, while the recording is still the neo extractor. The test mirrors the one in #2140.

Checked locally:
- the new test fails on `main` and passes with the change;
- the Axona tests in `test_recording_interfaces.py` go from 24 passed + the new test failing to
  25 passed, with the same two Zarr skips;
- `run_conversion` after `remove_channels`, without passing metadata, writes 15 of the 16 channels
  in their 4 tetrode groups, with the same start time;
- pre-commit hooks pass.

<!-- Not in this PR, your call whether to mention it or open an issue: AxonaUnitRecordingInterface
cannot be constructed on main. Its __init__ calls super().__init__(filename=file_path, noise_std=...),
which AxonaRecordingInterface does not accept: TypeError: AxonaRecordingInterface.__init__() got an
unexpected keyword argument 'filename'. It has no tests. -->
