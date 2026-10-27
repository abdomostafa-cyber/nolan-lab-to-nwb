# Draft issue for catalystneuro/neuroconv (SUPERSEDED, not posted)

> Superseded by `neuroconv-pr-description.md`: the fix goes upstream as a PR instead of an issue.
> Kept for the record of what was checked.

> **Status:** draft, not posted. Verified 2026-10-27 against `main` at `2c85f65`, which already
> includes #2140. Fix and test: `neuroconv-openephyslegacy-get-metadata-after-remove-channels.patch`
> (same folder), written in the same style as #2140.
> **Rewrite in your own words before posting**, and check open issues *and pull requests* again
> first. A keyword search missed #2140 the first time because it was only hours old.

---

**Title:** `[Bug]: OpenEphysLegacyRecordingInterface.get_metadata() raises AttributeError after remove_channels()`

### What happened?

#2140 fixed this for `AxonRecordingInterface`. `OpenEphysLegacyRecordingInterface` has the same
problem on current `main`: after `remove_channels(...)`, `get_metadata()` raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`, because it reads the
session start time through `self.recording_extractor.neo_reader`. `run_conversion()` without
explicit metadata fails the same way.

### Steps to Reproduce

```python
from neuroconv.datainterfaces import OpenEphysLegacyRecordingInterface

interface = OpenEphysLegacyRecordingInterface(folder_path=".../ephy_testing_data/openephys/OpenEphys_SampleData_1")
interface.remove_channels(channel_ids=[interface.channel_ids[-1]])
interface.get_metadata()  # AttributeError
```

### Traceback

```
  File ".../neuroconv/datainterfaces/ecephys/openephys/openephyslegacydatainterface.py", line 137, in get_metadata
    neo_reader = self.recording_extractor.neo_reader
AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'
```

### Possible fix

The same approach as #2140: keep the reader in `__init__`, while the recording is still the
neo-based extractor, and use it in `get_metadata`. I have this as a small PR with a regression test
mirroring the one in #2140, if you'd like it. Checked locally:

- the new test fails on current `main` and passes with the change;
- `tests/test_on_data/ecephys/test_openephyslegacy.py` and the OpenEphysLegacy tests in
  `test_recording_interfaces.py` give 17 passed + the new test failing before, and 18 passed after,
  with the same single Zarr skip. That includes `test_openephyslegacy_date_parse`, which edits the
  reader's annotations after construction.

**Not tested:** the same read inside `get_metadata`, or helpers it calls, is still there for
AlphaOmega, Axona, MaxOne, MEArec, Neuralynx and Plexon. I don't have their test data set up.

### Operating System
Windows 11

### Python Version
3.11.7

### Package Versions
neuroconv `main` (2c85f65) · spikeinterface 0.105.3 · neo 0.14.5

---

## Not filed: the other two rough edges

These stay in this project's DEVLOG and README; neither is a clear bug.

1. **NeuroConv: legacy start time cut to the date.** `'95534'` (09:55:34) triggers the "ambiguous"
   warning and only the date is kept. This is deliberate, and covered by
   `test_openephyslegacy_date_parse`.
2. **NWB Inspector: the CLI exits 0 even with CRITICAL findings.** That may be intended.
