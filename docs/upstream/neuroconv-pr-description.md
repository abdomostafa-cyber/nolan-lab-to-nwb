# PR description for catalystneuro/neuroconv

> **Status:** opened and merged 2026-10-27 as [catalystneuro/neuroconv#2141](https://github.com/catalystneuro/neuroconv/pull/2141) (merge commit `128578d`), from `abdomostafa-cyber:fix/openephyslegacy-get-metadata-after-remove-channels`
> on top of `main` at `2c85f65`: the fix (`c85dad1`) plus the changelog entry renamed to `2141.bugfix.md` (`296e2ef`).
> Below is the draft it started from; the posted text was edited by hand and adds a short introduction.

---

**Title:** Keep `OpenEphysLegacyRecordingInterface.get_metadata` working after `remove_channels`

**Body:**

#2140 fixed this for `AxonRecordingInterface`. `OpenEphysLegacyRecordingInterface` has the same
problem on `main`: after `remove_channels`, `get_metadata` raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`, because it reads the
session start time through `recording_extractor.neo_reader`. `run_conversion` without explicit
metadata fails the same way.

```python
interface = OpenEphysLegacyRecordingInterface(folder_path=OPENEPHYS_PATH / "OpenEphys_SampleData_1")
interface.remove_channels(channel_ids=[interface.channel_ids[-1]])
interface.get_metadata()  # AttributeError
```

Same approach as #2140: keep the reader in `__init__`, while the recording is still the neo
extractor. The test mirrors the one in #2140.

Checked locally:
- the new test fails on `main` and passes with the change;
- `test_openephyslegacy.py` and the OpenEphysLegacy tests in `test_recording_interfaces.py` pass,
  including `test_openephyslegacy_date_parse`, which edits the reader's annotations after
  construction;
- pre-commit hooks pass.

The same `recording_extractor.neo_reader` read inside `get_metadata` is still in the AlphaOmega,
Axona, MaxOne, MEArec, Neuralynx and Plexon interfaces. I left them out because I don't have their
test data to check them.

<!-- Optional, your call: "I found this while converting a legacy Open Ephys session, working with an
AI coding assistant; I've checked and can explain each change." -->
